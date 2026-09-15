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
    # a teardown closes a connection the device had already allowed
    "built": "Allowed", "teardown": "Allowed", "allow": "Allowed", "allowed": "Allowed",
    "accept": "Allowed", "permit": "Allowed", "permitted": "Allowed",
    "deny": "Denied", "denied": "Denied", "block": "Denied",
    "blocked": "Denied", "drop": "Denied",
}

_SCHEMAS: dict[int, dict] = {}


def _set_path(obj: dict, dotted_path: str, value) -> None:
    """Dotted OCSF path; a numeric segment indexes a list (evidences.0.src_endpoint.ip)."""
    parts = dotted_path.split(".")
    cur = obj
    for part, child in zip(parts, parts[1:]):
        if isinstance(cur, list):
            index = int(part)
            while len(cur) <= index:
                cur.append([] if child.isdigit() else {})
            cur = cur[index]
        else:
            cur = cur.setdefault(part, [] if child.isdigit() else {})
    if isinstance(cur, list):
        index = int(parts[-1])
        while len(cur) <= index:
            cur.append(None)
        cur[index] = value
    else:
        cur[parts[-1]] = value


def _get_path(obj: dict, dotted_path: str):
    cur = obj
    for p in dotted_path.split("."):
        if isinstance(cur, list) and p.isdigit() and int(p) < len(cur):
            cur = cur[int(p)]
        elif isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def _expected_json_type(schema: dict, dotted_path: str) -> str | None:
    node = schema
    for part in dotted_path.split("."):
        node = (node or {}).get("items") if part.isdigit() else (node or {}).get("properties", {}).get(part)
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


def _load_schema(class_uid: int) -> dict:
    """One vendored schema per OCSF class: core/ocsf/schema/*_<class_uid>.schema.json.
    A new class is a new schema file, not a code change."""
    if class_uid not in _SCHEMAS:
        path = next(SCHEMA_DIR.glob(f"*_{class_uid}.schema.json"), None)
        if path is None:
            raise ValueError(f"no vendored OCSF schema for class_uid {class_uid} in {SCHEMA_DIR}")
        _SCHEMAS[class_uid] = json.loads(path.read_text())
    return _SCHEMAS[class_uid]


class OCSFMapper:
    """Applies a source format's declarative YAML mapping to a ParsedEvent,
    producing a validated OCSF JSON event. New format support = new YAML
    file dropped in MAPPINGS_DIR — never a code change."""

    def __init__(self):
        self.mappings: dict[str, dict] = {}
        for yaml_file in MAPPINGS_DIR.rglob("*.yaml"):  # includes approved/ (human-approved AI-assist formats)
            mapping = yaml.safe_load(yaml_file.read_text())
            self.mappings[mapping["source_format"]] = mapping

    def register_mapping(self, mapping: dict) -> None:
        """Used by the AI-assist approval flow to hot-load a new mapping."""
        self.mappings[mapping["source_format"]] = mapping

    def has_mapping(self, source_format: str) -> bool:
        return source_format in self.mappings

    def map(self, event: ParsedEvent, mapping_confidence: float, raw_event_id: str) -> dict:
        mapping = self.mappings[event.source_format]
        schema = _load_schema(mapping["ocsf_class_uid"])

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
        # reserved parser key: the event's own timestamp as epoch ms. Kept out of YAML
        # field_maps, which double as the AI-assist example the local model imitates.
        if "event_time" in remaining_fields:
            out["time"] = remaining_fields.pop("event_time")
        value_maps = mapping.get("value_maps", {})
        for src_key, target_path in mapping.get("field_map", {}).items():
            if src_key not in remaining_fields:
                continue
            value = remaining_fields.pop(src_key)
            if src_key in value_maps:
                # vendor code -> OCSF value, declared in YAML (Suricata severity 2 -> severity_id 3)
                codes = value_maps[src_key]
                value = codes.get(value, codes.get("default", value))
            if target_path == "disposition":
                value = ACTION_DISPOSITION_MAP.get(str(value).lower(), str(value).title())
            else:
                value = _coerce_to_schema_type(value, _expected_json_type(schema, target_path))
            if target_path.endswith("connection_info.protocol_name"):
                value = value.lower()  # OCSF protocol names are lowercase ("tcp"), whatever the vendor logs
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

        jsonschema.validate(out, schema)
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
    assert ocsf_event["connection_info"]["protocol_name"] == "tcp"
    assert ocsf_event["src_endpoint"]["port"] == 52341
    assert ocsf_event["time"] == 1788099751000  # Aug 30 2026 14:22:31 UTC
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

    # Juniper SRX: protocol number and session action translate through the YAML value_maps
    from parsers.juniper_srx import JuniperSRXParser

    srx_deny = (
        b'<14>1 2026-08-30T19:45:12+05:30 SRX-EDGE-01 RT_FLOW - RT_FLOW_SESSION_DENY [junos@2636.1.1.1.2.40 '
        b'source-address="203.0.113.44" source-port="40110" destination-address="10.1.1.10" '
        b'destination-port="22" protocol-id="6" policy-name="UNTRUST-DENY" reason="policy deny"]'
    )
    srx = mapper.map(JuniperSRXParser().parse(srx_deny), mapping_confidence=0.95, raw_event_id="evt_srx")
    assert srx["disposition"] == "Denied" and srx["connection_info"]["protocol_name"] == "tcp"
    assert srx["time"] == 1788099312000 and srx["unmapped"]["policy-name"] == "UNTRUST-DENY"

    # Suricata alert -> Detection Finding (class 2004): endpoints go under evidences[0]
    from parsers.suricata_eve import SuricataEVEParser

    alert = (
        b'{"timestamp":"2026-08-30T19:45:02.123456+0530","event_type":"alert","src_ip":"203.0.113.44",'
        b'"src_port":40101,"dest_ip":"172.20.1.8","dest_port":23,"proto":"TCP","alert":{"action":"allowed",'
        b'"signature_id":2001219,"signature":"ET SCAN Potential SSH Scan",'
        b'"category":"Attempted Information Leak","severity":2}}'
    )
    finding = mapper.map(SuricataEVEParser().parse(alert), mapping_confidence=0.95, raw_event_id="evt_ids")
    assert (finding["class_uid"], finding["category_uid"], finding["type_uid"]) == (2004, 2, 200401)
    assert finding["finding_info"] == {
        "uid": "2001219", "title": "ET SCAN Potential SSH Scan", "types": ["Attempted Information Leak"]}
    assert finding["severity_id"] == 3 and finding["disposition"] == "Detected" and finding["time"] == 1788099302123
    assert finding["evidences"] == [{
        "src_endpoint": {"ip": "203.0.113.44", "port": 40101},
        "dst_endpoint": {"ip": "172.20.1.8", "port": 23},
        "connection_info": {"protocol_name": "tcp"},
    }], finding["evidences"]
    assert {"name": "evidences.0.src_endpoint.ip", "value": "203.0.113.44"} in finding["observables"]
    odd_severity = SuricataEVEParser().parse(alert.replace(b'"severity":2', b'"severity":9'))
    assert mapper.map(odd_severity, mapping_confidence=0.95, raw_event_id="evt_ids2")["severity_id"] == 99

    # Check Point: Reject translates to Denied via value_maps; time comes from the gateway's time field
    from parsers.checkpoint import CheckPointParser

    cp_reject = (
        b'<134>1 2026-08-30T14:06:03Z CP-GW-DC2 CheckPoint 26203 - [action:"Reject"; dst:"198.51.100.66"; '
        b'proto:"6"; rule_name:"Block direct SMTP"; s_port:"50110"; service:"25"; src:"10.1.2.21"; time:"1788098763"]'
    )
    cp = mapper.map(CheckPointParser().parse(cp_reject), mapping_confidence=0.95, raw_event_id="evt_cp")
    assert cp["disposition"] == "Denied" and cp["dst_endpoint"] == {"ip": "198.51.100.66", "port": 25}
    assert cp["connection_info"]["protocol_name"] == "tcp" and cp["time"] == 1788098763000
    print("ocsf mapper juniper + checkpoint + detection-finding demo: OK")


if __name__ == "__main__":
    demo()
