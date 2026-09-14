MAPPING_PROMPT_TEMPLATE = """You are helping map an unrecognized log format to the OCSF schema.

OCSF Network Activity (class_uid 4001) key fields:
{ocsf_class_schema}

Example mapping for a known format (Cisco ASA syslog):
{example_mapping_yaml}

New, unrecognized log samples:
{raw_samples}

Propose a YAML field mapping in the same structure as the example above.

CRITICAL — field_map direction, do not reverse it:
- Each KEY is a field name copied EXACTLY as it appears in the raw log
  samples above (e.g. the text immediately before an "=" sign, such as
  "srcip" or "spt" — not a renamed or normalized version of it).
- Each VALUE is one of the OCSF field paths listed above (e.g.
  "src_endpoint.ip", "dst_endpoint.port", "disposition") — never a raw
  field name, and never the same string as the key.

Map only fields you can confidently identify this way. Put anything
ambiguous under "unmapped_bucket". Respond with ONLY the YAML, no
explanation."""

OCSF_CLASS_SCHEMA_SUMMARY = """\
class_uid: 4001 (Network Activity), category_uid: 4
src_endpoint.ip, src_endpoint.port, dst_endpoint.ip, dst_endpoint.port
connection_info.protocol_name, disposition (Allowed/Denied)
metadata.product.name, metadata.product.vendor_name, metadata.version"""


def build_prompt(raw_samples: str, example_mapping_yaml: str) -> str:
    return MAPPING_PROMPT_TEMPLATE.format(
        ocsf_class_schema=OCSF_CLASS_SCHEMA_SUMMARY,
        example_mapping_yaml=example_mapping_yaml,
        raw_samples=raw_samples,
    )
