import re

from .base import BaseParser, ParsedEvent

# key="quoted value" or key=unquoted_token (FortiGate/generic key=value style —
# distinct from CEF's tokenizer, which must handle unquoted spaced values).
KV_PATTERN = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')


def tokenize(text: str) -> dict[str, str]:
    return {
        m.group(1): m.group(2) if m.group(2) is not None else m.group(3)
        for m in KV_PATTERN.finditer(text)
    }


class DynamicKVParser(BaseParser):
    """Generic key=value parser backing every AI-assist-approved format.
    One reusable implementation — approving a new format registers an
    instance of this with that format's known field names; it never
    generates a new parser class. Confidence is how much of the approved
    mapping's known field set actually shows up in a given line."""

    def __init__(self, source_format: str, known_keys: set[str]):
        self.source_format = source_format
        self._known_keys = known_keys
        self.field_keys = frozenset(known_keys)

    def detect(self, raw_bytes: bytes) -> float:
        if not self._known_keys:
            return 0.0
        tokens = tokenize(raw_bytes.decode(errors="ignore"))
        matched = len(self._known_keys & tokens.keys())
        return round(matched / len(self._known_keys), 2)

    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        tokens = tokenize(raw_bytes.decode(errors="ignore"))
        fields = {
            k: (int(v) if v.isdigit() else v)
            for k, v in tokens.items() if k in self._known_keys
        }
        unmapped = {k: v for k, v in tokens.items() if k not in self._known_keys}
        return ParsedEvent(
            source_format=self.source_format, raw_bytes=raw_bytes,
            fields=fields, unmapped=unmapped,
        )


def demo():
    sample = (
        b'date=2026-08-30 time=14:22:31 devname="FGT-EDGE-01" logid="0000000013" '
        b'type="traffic" srcip=10.5.2.14 dstip=203.0.113.44 dstport=8080 proto=6 '
        b'action="accept" policyid=12'
    )
    known_keys = {"srcip", "dstip", "dstport", "action"}
    parser = DynamicKVParser("fortigate_kv", known_keys)
    assert parser.detect(sample) == 1.0  # all 4 known keys present
    event = parser.parse(sample)
    assert event.fields == {"srcip": "10.5.2.14", "dstip": "203.0.113.44", "dstport": 8080, "action": "accept"}
    assert "devname" in event.unmapped and "policyid" in event.unmapped  # lossless

    unrelated = DynamicKVParser("fortigate_kv", known_keys)
    assert unrelated.detect(b"totally unrelated text with no equals signs") == 0.0
    print("generic_kv demo: OK", event.fields)


if __name__ == "__main__":
    demo()
