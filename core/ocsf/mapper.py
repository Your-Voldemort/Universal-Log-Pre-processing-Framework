import hashlib
import json
from pathlib import Path

import jsonschema
import yaml

from parsers.base import ParsedEvent

SCHEMA_DIR = Path(__file__).parent / "schema"
MAPPINGS_DIR = Path(__file__).parent / "mappings"

# Declarative action->disposition normalization, shared across all vendor
# mappings so a new format needs only a new YAML file, never new code.
ACTION_DISPOSITION_MAP = {
    "built": "Allowed", "allow": "Allowed", "allowed": "Allowed",
    "accept": "Allowed", "permit": "Allowed",
    "deny": "Denied", "denied": "Denied", "block": "Denied",
    "blocked": "Denied", "drop": "Denied", "teardown": "Denied",
}

_SCHEMA_CACHE: dict | None = None


def _set_path(obj: dict, dotted_path: str, value) -> None:
    parts = dotted_path.split(".")
    cur = obj
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def _get_path(obj: dict, dotted_path: str):
    cur = obj
    for p in dotted_path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _expected_json_type(schema: dict, dotted_path: str) -> str | None:
    node = schema
    for part in dotted_path.split("."):
        node = (node or {}).get("properties", {}).get(part)
        if node is None:
            return None
    return node.get("type")


def _coerce_to_schema_type(value, expected_type: str | None):
    """A raw parser guesses value types from syntax alone (numeric-looking
    text -> int) with no idea which OCSF field it'll end up in. Only the
    mapper knows the target's real type (from the vendored schema), so
    coercion has to happen here — e.g. a raw `proto=6` correctly parsed as
    int must become the string "6" if a mapping (commonly an AI-proposed
    one) points it at connection_info.protocol_name."""
    if expected_type == "string" and not isinstance(value, str):
        return str(value)
    if expected_type == "integer" and isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return value


def _load_schema() -> dict:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        with open(SCHEMA_DIR / "network_activity_4001.schema.json") as f:
            _SCHEMA_CACHE = json.load(f)
    return _SCHEMA_CACHE


class OCSFMapper:
    """Applies a source format's declarative YAML mapping to a ParsedEvent,
    producing a validated OCSF JSON event. New format support = new YAML
    file dropped in MAPPINGS_DIR — never a code change."""

    def __init__(self):
        self._mappings: dict[str, dict] = {}
        for yaml_file in MAPPINGS_DIR.glob("*.yaml"):
            mapping = yaml.safe_load(yaml_file.read_text())
            self._mappings[mapping["source_format"]] = mapping

    def register_mapping(self, mapping: dict) -> None:
        """Used by the AI-assist approval flow to hot-load a new mapping."""
        self._mappings[mapping["source_format"]] = mapping

    def has_mapping(self, source_format: str) -> bool:
        return source_format in self._mappings

    def map(self, event: ParsedEvent, mapping_confidence: float, raw_event_id: str) -> dict:
        mapping = self._mappings[event.source_format]

        out: dict = {
            "class_uid": mapping["ocsf_class_uid"],
            "category_uid": mapping["ocsf_category_uid"],
            "activity_id": mapping["activity_id"],
            "activity_name": mapping["activity_name"],
            "type_uid": mapping["ocsf_class_uid"] * 100 + mapping["activity_id"],
        }

        unmapped_bucket_name = mapping.get("unmapped_bucket", "unmapped")
        unmapped: dict = dict(event.unmapped)  # parser-level unmapped — never dropped

        remaining_fields = dict(event.fields)
        for src_key, target_path in mapping.get("field_map", {}).items():
            if src_key not in remaining_fields:
                continue
            value = remaining_fields.pop(src_key)
            if target_path == "disposition":
                value = ACTION_DISPOSITION_MAP.get(str(value).lower(), str(value).title())
            else:
                value = _coerce_to_schema_type(value, _expected_json_type(_load_schema(), target_path))
            _set_path(out, target_path, value)

        # anything the parser extracted but this mapping doesn't declare — lossless bucket
        unmapped.update(remaining_fields)

        for target_path, value in mapping.get("static_fields", {}).items():
            _set_path(out, target_path, value)

        out["observables"] = [
            {"name": path, "value": str(_get_path(out, path))}
            for path in mapping.get("observable_fields", [])
            if _get_path(out, path) is not None
        ]

        out[unmapped_bucket_name] = unmapped

        out["ulpf"] = {
            "raw_event_id": raw_event_id,
            "raw_event_hash": hashlib.sha256(event.raw_bytes).hexdigest(),
            "parser_version": f"{event.source_format}-1.0.0",
            "mapping_confidence": mapping_confidence,
        }

        jsonschema.validate(out, _load_schema())
        return out


def demo():
    from parsers.cisco_asa_syslog import CiscoASASyslogParser

    sample = (
        b"<166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound "
        b"TCP connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) "
        b"to inside:10.10.1.20/52341 (10.10.1.20/52341)"
    )
    event = CiscoASASyslogParser().parse(sample)
    mapper = OCSFMapper()
    ocsf_event = mapper.map(event, mapping_confidence=0.97, raw_event_id="evt_893823")

    assert ocsf_event["class_uid"] == 4001
    assert ocsf_event["category_uid"] == 4
    assert ocsf_event["src_endpoint"]["ip"] == "10.10.1.20"
    assert ocsf_event["dst_endpoint"] == {"ip": "172.16.1.50", "port": 443}
    assert ocsf_event["disposition"] == "Allowed"
    assert ocsf_event["metadata"]["product"]["name"] == "Cisco ASA"
    assert {"name": "src_endpoint.ip", "value": "10.10.1.20"} in ocsf_event["observables"]
    assert ocsf_event["ulpf"]["mapping_confidence"] == 0.97
    assert ocsf_event["ulpf"]["raw_event_id"] == "evt_893823"
    print("ocsf mapper demo: OK")
    print(json.dumps(ocsf_event, indent=2))

    # regression: an AI-proposed mapping pointed a raw numeric field (proto=6,
    # parsed as int by the generic KV parser) at a *string* OCSF target —
    # crashed jsonschema.validate before the mapper coerced by target type.
    from parsers.base import ParsedEvent

    numeric_proto_event = ParsedEvent(
        source_format="fortigate_kv_test",
        raw_bytes=b"srcip=10.5.2.14 dstip=203.0.113.44 dstport=8080 proto=6 action=accept",
        fields={"srcip": "10.5.2.14", "dstip": "203.0.113.44", "dstport": 8080, "proto": 6, "action": "accept"},
        unmapped={},
    )
    mapper.register_mapping({
        "source_format": "fortigate_kv_test",
        "ocsf_class_uid": 4001, "ocsf_category_uid": 4,
        "activity_id": 1, "activity_name": "Connection Attempt",
        "field_map": {
            "srcip": "src_endpoint.ip", "dstip": "dst_endpoint.ip",
            "dstport": "dst_endpoint.port", "proto": "connection_info.protocol_name",
            "action": "disposition",
        },
        "static_fields": {
            "metadata.product.name": "x", "metadata.product.vendor_name": "x", "metadata.version": "1.9.0",
        },
    })
    numeric_ocsf_event = mapper.map(numeric_proto_event, mapping_confidence=0.8, raw_event_id="evt_numeric")
    assert numeric_ocsf_event["connection_info"]["protocol_name"] == "6"  # coerced int -> str
    print("ocsf mapper numeric-target-type demo: OK")


if __name__ == "__main__":
    demo()
