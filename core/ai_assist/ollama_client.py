import os
import re

import httpx
import yaml

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

REQUIRED_MAPPING_KEYS = {"source_format", "ocsf_class_uid", "ocsf_category_uid", "field_map"}

# The only OCSF targets ULPF's mapper actually understands (see
# ocsf/mapper.py's _set_path usage + the vendored schema). A small local
# model will sometimes invert field_map — putting a raw field name on both
# sides instead of {raw_name: ocsf_path} — which silently produces an event
# missing "disposition" and fails schema validation downstream. Reject that
# here, at proposal time, instead of letting a rushed human approve it.
VALID_OCSF_TARGETS = {
    "src_endpoint.ip", "src_endpoint.port",
    "dst_endpoint.ip", "dst_endpoint.port",
    "connection_info.protocol_name", "disposition",
}

_CODE_FENCE = re.compile(r"^```(?:yaml)?\s*|\s*```$", re.MULTILINE)

# source_format becomes a filename (ocsf/mappings/approved/<name>.yaml) and comes from
# model output that raw log text can steer — plain names only, no path characters.
SOURCE_FORMAT_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}")


def extract_yaml(model_response_text: str) -> str:
    return _CODE_FENCE.sub("", model_response_text).strip()


def parse_and_validate_mapping(yaml_text: str) -> dict:
    mapping = yaml.safe_load(yaml_text)
    if not isinstance(mapping, dict):
        raise ValueError("model did not return a YAML mapping object")
    missing = REQUIRED_MAPPING_KEYS - mapping.keys()
    if missing:
        raise ValueError(f"proposed mapping missing required keys: {missing}")
    if not isinstance(mapping["source_format"], str) or not SOURCE_FORMAT_NAME.fullmatch(mapping["source_format"]):
        raise ValueError(f"source_format {mapping['source_format']!r} must be a plain name like fortigate_kv")

    field_map = mapping["field_map"]
    if not isinstance(field_map, dict) or not field_map:
        raise ValueError("field_map must be a non-empty mapping of raw field name -> OCSF path")
    bad_targets = {v for v in field_map.values() if v not in VALID_OCSF_TARGETS}
    if bad_targets:
        raise ValueError(
            f"field_map has invalid OCSF target path(s) {bad_targets} — did the model reverse "
            f"key/value? Keys must be raw field names, values must be one of {VALID_OCSF_TARGETS}"
        )
    inverted = {k for k, v in field_map.items() if k == v}
    if inverted:
        raise ValueError(f"field_map key(s) {inverted} are identical to their value — looks reversed")

    mapping.setdefault("activity_id", 1)
    mapping.setdefault("activity_name", "Connection Attempt")
    mapping.setdefault("unmapped_bucket", "unmapped")
    mapping.setdefault("observable_fields", ["src_endpoint.ip", "dst_endpoint.ip"])

    # the OCSF schema requires a metadata.product/version block — backfill it
    # from the source format name if the model's proposal omitted it, so an
    # under-specified AI proposal can never produce a schema-invalid event.
    static_fields = mapping.setdefault("static_fields", {})
    static_fields.setdefault("metadata.product.name", mapping["source_format"])
    static_fields.setdefault("metadata.product.vendor_name", "Unverified (AI-assisted mapping)")
    static_fields.setdefault("metadata.version", "1.9.0")
    return mapping


def propose_mapping(prompt: str, timeout: float = 60.0) -> str:
    """Call the local Ollama model — no cloud call, offline-first. Returns
    raw YAML text; the caller (routes_mapping.py) validates and stores it
    as a *proposal* only. It never becomes an active parser without an
    explicit human /approve call."""
    resp = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    resp.raise_for_status()
    return extract_yaml(resp.json()["response"])


def demo():
    # Exercises the parsing/validation path without requiring a live Ollama
    # server, so this check runs anywhere. propose_mapping() itself is a
    # thin, untested-here HTTP call — see routes_mapping.py for the live path.
    fake_model_response = """```yaml
source_format: fortigate_kv
ocsf_class_uid: 4001
ocsf_category_uid: 4
field_map:
  srcip: src_endpoint.ip
  dstip: dst_endpoint.ip
  dstport: dst_endpoint.port
  action: disposition
```"""
    yaml_text = extract_yaml(fake_model_response)
    mapping = parse_and_validate_mapping(yaml_text)
    assert mapping["source_format"] == "fortigate_kv"
    assert mapping["field_map"]["srcip"] == "src_endpoint.ip"
    assert mapping["activity_name"] == "Connection Attempt"  # default filled in

    # source_format is used as a filename: path characters must never get through
    for bad_name in ("../../parsers/registry", "a/b", "'fortigate kv'", "''"):
        try:
            parse_and_validate_mapping(yaml_text.replace("source_format: fortigate_kv", f"source_format: {bad_name}"))
            raise AssertionError(f"should have rejected source_format {bad_name}")
        except ValueError:
            pass

    try:
        parse_and_validate_mapping("just: a\nrandom: mapping")
        raise AssertionError("should have rejected a mapping missing required keys")
    except ValueError:
        pass

    # regression: a small local model observed reversing field_map direction
    # (raw name on both sides) instead of {raw_name: ocsf_path} — must be
    # rejected at proposal time, not silently approved.
    inverted_response = """source_format: fortigate_kv
ocsf_class_uid: 4001
ocsf_category_uid: 4
field_map:
  srcip: srcip
  dstip: dstip
  action: action
"""
    try:
        parse_and_validate_mapping(inverted_response)
        raise AssertionError("should have rejected a mapping with reversed field_map")
    except ValueError:
        pass

    print("ollama_client demo: OK")


if __name__ == "__main__":
    demo()
