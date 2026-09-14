import re

from .base import BaseParser, ParsedEvent

# <166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound TCP
# connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) to
# inside:10.10.1.20/52341 (10.10.1.20/52341)
ASA_SIGNATURE = re.compile(r"%ASA-\d-\d+")
BUILT_CONN = re.compile(
    r"Built (?P<direction>\w+) (?P<proto>\w+) connection \d+ "
    r"for \w+:(?P<dst_ip>[\d.]+)/(?P<dst_port>\d+) .*? "
    r"to \w+:(?P<src_ip>[\d.]+)/(?P<src_port>\d+)"
)


class CiscoASASyslogParser(BaseParser):
    source_format = "cisco_asa_syslog"

    def detect(self, raw_bytes: bytes) -> float:
        text = raw_bytes.decode(errors="ignore")
        if ASA_SIGNATURE.search(text) and "Built" in text:
            return 0.95
        return 0.0

    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        text = raw_bytes.decode(errors="ignore")
        match = BUILT_CONN.search(text)
        fields: dict = {}
        unmapped: dict = {}
        if match:
            g = match.groupdict()
            fields = {
                "src_ip": g["src_ip"],
                "dst_ip": g["dst_ip"],
                "src_port": int(g["src_port"]),
                "dst_port": int(g["dst_port"]),
                "proto": g["proto"].upper(),
                "action": "Built",
            }
        else:
            unmapped["raw_text"] = text
        return ParsedEvent(
            source_format=self.source_format,
            raw_bytes=raw_bytes,
            fields=fields,
            unmapped=unmapped,
        )


def demo():
    sample = (
        b"<166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound "
        b"TCP connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) "
        b"to inside:10.10.1.20/52341 (10.10.1.20/52341)"
    )
    parser = CiscoASASyslogParser()
    assert parser.detect(sample) >= 0.7
    event = parser.parse(sample)
    assert event.fields["src_ip"] == "10.10.1.20"
    assert event.fields["dst_ip"] == "172.16.1.50"
    assert event.fields["src_port"] == 52341
    assert event.fields["dst_port"] == 443
    assert event.fields["proto"] == "TCP"
    print("cisco_asa_syslog demo: OK", event.fields)


if __name__ == "__main__":
    demo()
