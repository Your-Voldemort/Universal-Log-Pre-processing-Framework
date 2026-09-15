import re

from .base import BaseParser, ParsedEvent, to_epoch_ms

# CEF extension values may contain spaces (e.g. rt=Aug 30 2026 14:22:31),
# so tokens can't be split on whitespace — split on "key=" boundaries instead.
KV_KEY_BOUNDARY = re.compile(r"(\w+)=")

CEF_HEADER_FIELDS = [
    "cef_version", "device_vendor", "device_product", "device_version",
    "signature_id", "name", "severity",
]

KNOWN_KV_FIELDS = {
    "src": "src_ip",
    "dst": "dst_ip",
    "spt": "src_port",
    "dpt": "dst_port",
    "proto": "proto",
    "act": "action",
}
INT_FIELDS = {"src_port", "dst_port"}


class PaloAltoCEFParser(BaseParser):
    source_format = "paloalto_cef"
    field_keys = frozenset((*KNOWN_KV_FIELDS.values(), "event_time"))

    def detect(self, raw_bytes: bytes) -> float:
        text = raw_bytes.decode(errors="ignore")
        if text.startswith("CEF:0|Palo Alto Networks|"):
            return 0.95
        if text.startswith("CEF:"):
            return 0.4
        return 0.0

    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        text = raw_bytes.decode(errors="ignore")
        # CEF header is exactly 7 pipe-delimited fields (Version..Severity);
        # everything after the 7th pipe is the extension. Severity varies
        # (0-10 in real logs — denied/blocked traffic is often >1), so it
        # can't be used as a literal split boundary.
        header_parts = text.split("|", 7)
        extension = header_parts.pop() if len(header_parts) == 8 else ""

        fields: dict = {}
        unmapped: dict = {}

        for name, value in zip(CEF_HEADER_FIELDS, header_parts):
            unmapped[name] = value

        matches = list(KV_KEY_BOUNDARY.finditer(extension))
        for i, m in enumerate(matches):
            key = m.group(1)
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(extension)
            value = extension[start:end].strip()
            if key in KNOWN_KV_FIELDS:
                mapped_key = KNOWN_KV_FIELDS[key]
                fields[mapped_key] = int(value) if mapped_key in INT_FIELDS else value
            else:
                unmapped[key] = value  # includes rt (timestamp) — never dropped

        # rt stays verbatim in unmapped; its parsed form feeds OCSF time.
        # CEF allows either epoch ms or "MMM dd yyyy HH:mm:ss".
        rt = unmapped.get("rt", "")
        event_time = int(rt) if rt.isdigit() else to_epoch_ms(rt)
        if event_time is not None:
            fields["event_time"] = event_time

        return ParsedEvent(
            source_format=self.source_format,
            raw_bytes=raw_bytes,
            fields=fields,
            unmapped=unmapped,
        )


def demo():
    from datetime import datetime, timezone

    sample = (
        b"CEF:0|Palo Alto Networks|PAN-OS|11.0.0|traffic|traffic-allow|1|"
        b"rt=Aug 30 2026 14:22:31 src=10.2.4.21 dst=172.20.1.8 spt=52341 "
        b"dpt=443 proto=tcp act=allow deviceExternalId=PA-VM-01"
    )
    parser = PaloAltoCEFParser()
    assert parser.detect(sample) >= 0.7
    event = parser.parse(sample)
    assert event.fields["src_ip"] == "10.2.4.21"
    assert event.fields["dst_ip"] == "172.20.1.8"
    assert event.fields["src_port"] == 52341
    assert event.fields["dst_port"] == 443
    assert event.fields["proto"] == "tcp"
    assert event.fields["action"] == "allow"
    assert event.unmapped["deviceExternalId"] == "PA-VM-01"
    assert event.unmapped["rt"] == "Aug 30 2026 14:22:31"
    assert event.fields["event_time"] == int(datetime(2026, 8, 30, 14, 22, 31, tzinfo=timezone.utc).timestamp() * 1000)

    # severity is not always 1 — a denied/blocked event commonly logs higher
    # (e.g. 3) — regression check for a real bug found generating demo data.
    deny_sample = (
        b"CEF:0|Palo Alto Networks|PAN-OS|11.0.0|traffic|traffic-deny|3|"
        b"rt=Aug 30 2026 14:15:01 src=203.0.113.44 dst=172.20.1.8 spt=40100 "
        b"dpt=21 proto=tcp act=deny deviceExternalId=PA-VM-01"
    )
    deny_event = parser.parse(deny_sample)
    assert deny_event.fields["src_ip"] == "203.0.113.44", deny_event.fields
    assert deny_event.fields["action"] == "deny"
    assert deny_event.unmapped["severity"] == "3"

    print("paloalto_cef demo: OK", event.fields)


if __name__ == "__main__":
    demo()
