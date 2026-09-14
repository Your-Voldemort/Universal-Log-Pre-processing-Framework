from .base import BaseParser

CONFIDENCE_THRESHOLD = 0.7


class ParserRegistry:
    def __init__(self):
        self._parsers: list[BaseParser] = []

    def register(self, parser: BaseParser):
        self._parsers.append(parser)

    def route(self, raw_bytes: bytes) -> tuple[BaseParser | None, float]:
        """Return (best_parser, confidence). None if confidence < threshold —
        triggers the AI-assist path."""
        scored = [(p, p.detect(raw_bytes)) for p in self._parsers]
        best = max(scored, key=lambda x: x[1], default=(None, 0.0))
        return best if best[1] >= CONFIDENCE_THRESHOLD else (None, best[1])

    def get(self, source_format: str) -> BaseParser | None:
        for p in self._parsers:
            if p.source_format == source_format:
                return p
        return None


def build_default_registry() -> ParserRegistry:
    from .cisco_asa_syslog import CiscoASASyslogParser
    from .paloalto_cef import PaloAltoCEFParser

    registry = ParserRegistry()
    registry.register(CiscoASASyslogParser())
    registry.register(PaloAltoCEFParser())
    return registry


def demo():
    registry = build_default_registry()

    cisco_sample = (
        b"<166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound "
        b"TCP connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) "
        b"to inside:10.10.1.20/52341 (10.10.1.20/52341)"
    )
    paloalto_sample = (
        b"CEF:0|Palo Alto Networks|PAN-OS|11.0.0|traffic|traffic-allow|1|"
        b"rt=Aug 30 2026 14:22:31 src=10.2.4.21 dst=172.20.1.8 spt=52341 "
        b"dpt=443 proto=tcp act=allow deviceExternalId=PA-VM-01"
    )
    unknown_sample = (
        b'date=2026-08-30 time=14:22:31 devname="FGT-EDGE-01" logid="0000000013" '
        b'type="traffic" srcip=10.5.2.14 dstip=203.0.113.44 dstport=8080 proto=6 '
        b'action="accept" policyid=12'
    )

    parser, conf = registry.route(cisco_sample)
    assert parser is not None and parser.source_format == "cisco_asa_syslog" and conf >= 0.7

    parser, conf = registry.route(paloalto_sample)
    assert parser is not None and parser.source_format == "paloalto_cef" and conf >= 0.7

    parser, conf = registry.route(unknown_sample)
    assert parser is None, "unknown format must not match a known parser"

    print("registry demo: OK (both known formats routed, unknown format falls through)")


if __name__ == "__main__":
    demo()
