import re

from .base import BaseParser, ParsedEvent, to_epoch_ms

# <166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound TCP connection ...
SYSLOG_HEADER = re.compile(
    r"^<(?P<syslog_pri>\d+)>(?P<syslog_timestamp>\w{3} +\d{1,2} \d{4} \d{2}:\d{2}:\d{2})"
    r"(?: (?P<device_name>[^\s%:]+))?"
)
ASA_MESSAGE = re.compile(r"%ASA-(?P<severity>\d)-(?P<message_id>\d+): (?P<message>.*)")

# One pattern per supported ASA message family. Named groups outside the flow
# 5-tuple (zones, direction, connection id, ACL) land in unmapped, never dropped.
FLOW_PATTERNS = [
    # 302013/302015 Built outbound TCP connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) to inside:10.10.1.20/52341 (10.10.1.20/52341)
    # 302014/302016 Teardown TCP connection 8847123 for outside:172.16.1.50/443 to inside:10.10.1.20/52341 duration 0:01:02 bytes 5120 TCP FINs
    re.compile(
        r"(?P<action>Built|Teardown)(?: (?P<direction>inbound|outbound))? (?P<proto>TCP|UDP) "
        r"connection (?P<connection_id>\d+) for (?P<for_zone>[\w.-]+):(?P<for_ip>[\d.]+)/(?P<for_port>\d+)"
        r"(?: \([^)]*\))* to (?P<to_zone>[\w.-]+):(?P<to_ip>[\d.]+)/(?P<to_port>\d+)"
    ),
    # 106023 Deny tcp src outside:203.0.113.44/40100 dst inside:10.10.1.20/22 by access-group "OUTSIDE_IN" [0x0, 0x0]
    re.compile(
        r"(?P<action>Deny) (?P<proto>\w+) src (?P<src_zone>[\w.-]+):(?P<src_ip>[\d.]+)(?:/(?P<src_port>\d+))? "
        r"dst (?P<dst_zone>[\w.-]+):(?P<dst_ip>[\d.]+)(?:/(?P<dst_port>\d+))?"
        r"(?: \([^)]*\))?(?: by access-group \"(?P<acl>[^\"]+)\")?"
    ),
    # 106001 Inbound TCP connection denied from 203.0.113.44/40100 to 10.10.1.20/22 flags SYN on interface outside
    re.compile(
        r"Inbound (?P<proto>TCP) connection (?P<action>denied) "
        r"from (?P<src_ip>[\d.]+)/(?P<src_port>\d+) to (?P<dst_ip>[\d.]+)/(?P<dst_port>\d+)"
    ),
    # 106006 Deny inbound UDP from 203.0.113.44/5353 to 10.10.1.20/161 on interface outside
    # 106015 Deny TCP (no connection) from 10.10.1.20/443 to 203.0.113.44/40100 flags RST on interface inside
    re.compile(
        r"(?P<action>Deny) (?:inbound )?(?P<proto>TCP|UDP)(?: \(no connection\))? "
        r"from (?P<src_ip>[\d.]+)/(?P<src_port>\d+) to (?P<dst_ip>[\d.]+)/(?P<dst_port>\d+)"
    ),
    # 106100 access-list OUTSIDE_IN denied tcp outside/203.0.113.44(40102) -> inside/10.10.1.20(25) hit-cnt 1 first hit [0x1a2b3c4d, 0x0]
    re.compile(
        r"access-list (?P<acl>\S+) (?P<action>denied|permitted) (?P<proto>\w+) "
        r"(?P<src_zone>[\w.-]+)/(?P<src_ip>[\d.]+)\((?P<src_port>\d+)\) -> "
        r"(?P<dst_zone>[\w.-]+)/(?P<dst_ip>[\d.]+)\((?P<dst_port>\d+)\)"
    ),
]
FLOW_KEYS = ("src_ip", "dst_ip", "src_port", "dst_port", "proto", "action")
PORT_KEYS = {"src_port", "dst_port"}


def match_flow(message: str) -> dict | None:
    for pattern in FLOW_PATTERNS:
        m = pattern.search(message)
        if m:
            g = {k: v for k, v in m.groupdict().items() if v is not None}
            break
    else:
        return None
    if "for_ip" in g:
        # 302013-302016 name a "for" side and a "to" side: inbound connections were
        # initiated from the "for" side, outbound from the "to" side. Teardown logs
        # no direction, so it is oriented like outbound; zones stay in unmapped.
        src, dst = ("for", "to") if g.get("direction") == "inbound" else ("to", "for")
        for side, role in ((src, "src"), (dst, "dst")):
            for part in ("zone", "ip", "port"):
                g[f"{role}_{part}"] = g.pop(f"{side}_{part}")
    return g


class CiscoASASyslogParser(BaseParser):
    source_format = "cisco_asa_syslog"

    def detect(self, raw_bytes: bytes) -> float:
        asa = ASA_MESSAGE.search(raw_bytes.decode(errors="ignore"))
        if asa is None:
            return 0.0
        # an ASA line whose message ID has no flow pattern here can't be mapped
        # confidently: it falls through to unknown_format / AI-assist, raw bytes kept
        return 0.95 if match_flow(asa["message"]) else 0.5

    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        text = raw_bytes.decode(errors="ignore").strip()
        fields: dict = {}
        unmapped: dict = {}

        header = SYSLOG_HEADER.match(text)
        if header:
            unmapped.update({k: v for k, v in header.groupdict().items() if v is not None})
            event_time = to_epoch_ms(header["syslog_timestamp"])
            if event_time is not None:
                fields["event_time"] = event_time

        asa = ASA_MESSAGE.search(text)
        if asa is None:
            unmapped["raw_text"] = text
        else:
            unmapped.update(asa.groupdict())
            flow = match_flow(asa["message"]) or {}
            for key in FLOW_KEYS:
                if key in flow:
                    value = flow.pop(key)
                    fields[key] = int(value) if key in PORT_KEYS else value
            unmapped.update(flow)  # zones, direction, connection id, ACL

        return ParsedEvent(
            source_format=self.source_format,
            raw_bytes=raw_bytes,
            fields=fields,
            unmapped=unmapped,
        )


def demo():
    from datetime import datetime, timezone

    parser = CiscoASASyslogParser()
    header = b"<166>Aug 30 2026 14:22:31 ASA-FW01 : "
    sample = header + (
        b"%ASA-6-302013: Built outbound TCP connection 8847123 for outside:172.16.1.50/443 "
        b"(172.16.1.50/443) to inside:10.10.1.20/52341 (10.10.1.20/52341)"
    )
    assert parser.detect(sample) >= 0.7
    event = parser.parse(sample)
    assert event.fields == {
        "event_time": int(datetime(2026, 8, 30, 14, 22, 31, tzinfo=timezone.utc).timestamp() * 1000),
        "src_ip": "10.10.1.20", "dst_ip": "172.16.1.50", "src_port": 52341, "dst_port": 443,
        "proto": "TCP", "action": "Built",
    }, event.fields
    # lossless: everything outside the flow 5-tuple is kept in unmapped
    assert event.unmapped["device_name"] == "ASA-FW01" and event.unmapped["message_id"] == "302013"
    assert event.unmapped["syslog_timestamp"] == "Aug 30 2026 14:22:31"
    assert event.unmapped["connection_id"] == "8847123" and event.unmapped["direction"] == "outbound"
    assert (event.unmapped["src_zone"], event.unmapped["dst_zone"]) == ("inside", "outside")

    # (message, src_ip, src_port, dst_ip, dst_port, action)
    cases = [
        (b"%ASA-6-302013: Built inbound TCP connection 8847001 for outside:198.51.100.7/51234 "
         b"(198.51.100.7/51234) to dmz:10.10.2.15/443 (203.0.113.10/443)",
         "198.51.100.7", 51234, "10.10.2.15", 443, "Built"),
        (b"%ASA-6-302014: Teardown TCP connection 8847123 for outside:172.16.1.50/443 "
         b"to inside:10.10.1.20/52341 duration 0:01:02 bytes 5120 TCP FINs",
         "10.10.1.20", 52341, "172.16.1.50", 443, "Teardown"),
        (b"%ASA-6-302016: Teardown UDP connection 8847124 for outside:172.16.1.51/53 "
         b"to inside:10.10.1.21/49037 duration 0:00:54 bytes 212",
         "10.10.1.21", 49037, "172.16.1.51", 53, "Teardown"),
        (b'%ASA-4-106023: Deny tcp src outside:203.0.113.44/40100 dst inside:10.10.1.20/22 '
         b'by access-group "OUTSIDE_IN" [0x0, 0x0]',
         "203.0.113.44", 40100, "10.10.1.20", 22, "Deny"),
        (b"%ASA-2-106001: Inbound TCP connection denied from 203.0.113.44/40101 to 10.10.1.20/23 "
         b"flags SYN on interface outside",
         "203.0.113.44", 40101, "10.10.1.20", 23, "denied"),
        (b"%ASA-2-106006: Deny inbound UDP from 203.0.113.44/5353 to 10.10.1.20/161 on interface outside",
         "203.0.113.44", 5353, "10.10.1.20", 161, "Deny"),
        (b"%ASA-6-106015: Deny TCP (no connection) from 10.10.1.20/443 to 203.0.113.44/40100 "
         b"flags RST  on interface inside",
         "10.10.1.20", 443, "203.0.113.44", 40100, "Deny"),
        (b"%ASA-6-106100: access-list OUTSIDE_IN denied tcp outside/203.0.113.44(40102) -> "
         b"inside/10.10.1.20(25) hit-cnt 1 first hit [0x1a2b3c4d, 0x0]",
         "203.0.113.44", 40102, "10.10.1.20", 25, "denied"),
    ]
    for message, src_ip, src_port, dst_ip, dst_port, action in cases:
        line = header + message
        assert parser.detect(line) >= 0.7, message
        f = parser.parse(line).fields
        assert (f["src_ip"], f["src_port"], f["dst_ip"], f["dst_port"], f["action"]) == (
            src_ip, src_port, dst_ip, dst_port, action), (message, f)

    icmp = parser.parse(header + b'%ASA-4-106023: Deny icmp src outside:203.0.113.44 dst inside:10.10.1.20 '
                                 b'(type 8, code 0) by access-group "OUTSIDE_IN" [0x0, 0x0]')
    assert icmp.fields["action"] == "Deny" and "dst_port" not in icmp.fields
    assert icmp.unmapped["acl"] == "OUTSIDE_IN"

    # recognized ASA, unsupported message: stays raw and routes to unknown_format / AI-assist
    unsupported = header + b"%ASA-6-305011: Built dynamic TCP translation from inside:10.10.1.20/52341 to outside:203.0.113.10/52341"
    assert parser.detect(unsupported) < 0.7
    print("cisco_asa_syslog demo: OK", event.fields)


if __name__ == "__main__":
    demo()
