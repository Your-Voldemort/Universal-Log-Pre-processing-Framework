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
    from .checkpoint import CheckPointParser
    from .cisco_asa_syslog import CiscoASASyslogParser
    from .juniper_srx import JuniperSRXParser
    from .paloalto_cef import PaloAltoCEFParser
    from .suricata_eve import SuricataEVEParser

    registry = ParserRegistry()
    registry.register(CiscoASASyslogParser())
    registry.register(PaloAltoCEFParser())
    registry.register(JuniperSRXParser())
    registry.register(SuricataEVEParser())
    registry.register(CheckPointParser())
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

    for source_format, sample in (
        ("juniper_srx_rt_flow", b'<14>1 2026-08-30T14:22:31Z SRX-EDGE-01 RT_FLOW - RT_FLOW_SESSION_DENY '
            b'[junos@2636.1.1.1.2.40 source-address="203.0.113.44" source-port="40110" '
            b'destination-address="10.1.1.10" destination-port="22" protocol-id="6"]'),
        ("suricata_eve", b'{"timestamp":"2026-08-30T14:22:31Z","event_type":"alert","src_ip":"203.0.113.44",'
            b'"dest_ip":"172.20.1.8","proto":"ICMP","alert":{"action":"allowed","signature_id":2100384,'
            b'"signature":"GPL ICMP_INFO PING","category":"Misc activity","severity":3}}'),
        ("checkpoint_log_exporter", b'<134>1 2026-08-30T14:15:21Z CP-GW-DC2 CheckPoint 26203 - [action:"Drop"; '
            b'dst:"10.1.2.5"; proto:"6"; s_port:"40112"; service:"445"; src:"203.0.113.44"; time:"1788099321"]'),
    ):
        parser, conf = registry.route(sample)
        assert parser is not None and parser.source_format == source_format and conf >= 0.7, source_format

    parser, conf = registry.route(unknown_sample)
    assert parser is None, "unknown format must not match a known parser"

    print("registry demo: OK (all 5 built-in formats routed, unknown format falls through)")


if __name__ == "__main__":
    demo()
