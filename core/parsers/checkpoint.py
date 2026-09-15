import re

from .base import BaseParser, ParsedEvent, iso_to_epoch_ms

# Check Point Log Exporter, syslog format:
# <134>1 2026-08-30T14:05:10Z CP-GW-DC2 CheckPoint 26203 - [action:"Accept"; ifdir:"outbound"; ... src:"10.1.2.20"; s_port:"51877"; dst:"198.51.100.30"; service:"443"; proto:"6"; time:"1788098710"]
LOG_EXPORTER = re.compile(
    r"^<(?P<syslog_pri>\d+)>1 (?P<syslog_timestamp>\S+) (?P<device_name>\S+) CheckPoint "
    r"(?P<proc_id>\S+) (?P<msg_id>\S+) \[(?P<params>.*)\]$"
)
FIELD = re.compile(r'(\w+):"((?:[^"\\]|\\.)*)"')

# Log Exporter key -> ULPF field. Every other key (rule, zones, interface, NAT xlate*,
# loguid, origin gateway, policy tag, the original time) lands in unmapped, never dropped.
KNOWN_KEYS = {
    "src": "src_ip", "dst": "dst_ip", "s_port": "src_port", "service": "dst_port",
    "proto": "proto", "action": "action",
}
INT_FIELDS = {"src_port", "dst_port", "proto"}
# firewall-blade connection verdicts; threat-prevention verdicts (Detect, Prevent, ...) aren't connections
CONNECTION_ACTIONS = {"Accept", "Drop", "Reject"}


class CheckPointParser(BaseParser):
    source_format = "checkpoint_log_exporter"
    field_keys = frozenset((*KNOWN_KEYS.values(), "event_time"))

    def detect(self, raw_bytes: bytes) -> float:
        text = raw_bytes.decode(errors="ignore").strip()
        m = LOG_EXPORTER.match(text)
        if m:
            params = dict(FIELD.findall(m["params"]))
            if params.get("action") in CONNECTION_ACTIONS and "src" in params and "dst" in params:
                return 0.95
        # Check Point, but a threat log or another export layout (CEF, LEEF): stays raw
        return 0.5 if "CheckPoint" in text or "Check Point" in text else 0.0

    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        text = raw_bytes.decode(errors="ignore").strip()
        m = LOG_EXPORTER.match(text)
        if m is None:
            return ParsedEvent(self.source_format, raw_bytes, {}, {"raw_text": text})

        unmapped = {k: v for k, v in m.groupdict().items() if k != "params"}
        fields: dict = {}
        for key, value in FIELD.findall(m["params"]):
            name = KNOWN_KEYS.get(key)
            if name is None:
                unmapped[key] = value
            else:
                fields[name] = int(value) if name in INT_FIELDS and value.isdigit() else value
        # the gateway's own log time (epoch seconds, kept verbatim in unmapped); header time as fallback
        log_time = unmapped.get("time", "")
        event_time = int(log_time) * 1000 if log_time.isdigit() else iso_to_epoch_ms(m["syslog_timestamp"])
        if event_time is not None:
            fields["event_time"] = event_time
        return ParsedEvent(self.source_format, raw_bytes, fields, unmapped)


def demo():
    parser = CheckPointParser()
    accept = (
        b'<134>1 2026-08-30T14:05:10Z CP-GW-DC2 CheckPoint 26203 - [action:"Accept"; flags:"411908"; '
        b'ifdir:"outbound"; ifname:"eth2"; loguid:"{0x6a2f1a11,0x0,0x3,0x7}"; origin:"192.0.2.40"; '
        b'time:"1788098710"; version:"5"; '
        b'__policy_id_tag:"product=VPN-1 & FireWall-1[db_tag={6A2F};mgmt=cp-mgmt;policy_name=Standard\\]"; '
        b'dst:"198.51.100.30"; inzone:"Internal"; outzone:"External"; proto:"6"; rule_name:"Outbound web"; '
        b's_port:"51877"; service:"443"; service_id:"https"; src:"10.1.2.20"; xlatesrc:"203.0.113.9"]'
    )
    assert parser.detect(accept) >= 0.7
    event = parser.parse(accept)
    assert event.fields == {
        "action": "Accept", "dst_ip": "198.51.100.30", "proto": 6, "src_port": 51877, "dst_port": 443,
        "src_ip": "10.1.2.20", "event_time": 1788098710000,  # 14:05:10 UTC, from the time field
    }, event.fields
    assert set(event.fields) <= parser.field_keys
    # lossless: rule, NAT, gateway and the escaped policy tag stay in unmapped verbatim
    assert event.unmapped["rule_name"] == "Outbound web" and event.unmapped["xlatesrc"] == "203.0.113.9"
    assert event.unmapped["time"] == "1788098710" and event.unmapped["device_name"] == "CP-GW-DC2"
    assert event.unmapped["__policy_id_tag"].endswith("policy_name=Standard\\]")

    icmp = parser.parse(
        b'<134>1 2026-08-30T14:14:59Z CP-GW-DC2 CheckPoint 26203 - [action:"Drop"; dst:"10.1.2.5"; '
        b'icmp:"Echo Request"; icmp_type:"8"; proto:"1"; rule_name:"Cleanup rule"; src:"203.0.113.44"]'
    )
    assert icmp.fields["action"] == "Drop" and "dst_port" not in icmp.fields
    assert icmp.fields["event_time"] == 1788099299000  # no time field: header timestamp fallback

    threat = (b'<134>1 2026-08-30T14:15:30Z CP-GW-DC2 CheckPoint 26203 - [action:"Detect"; product:"IPS"; '
              b'src:"203.0.113.44"; dst:"10.1.2.5"; attack:"Port Scan"]')
    assert 0 < parser.detect(threat) < 0.7  # threat-prevention log, not a connection: stays raw
    cef = b"CEF:0|Check Point|VPN-1 & FireWall-1|Check Point|Accept|https|Unknown|act=Accept src=10.1.2.20"
    assert 0 < parser.detect(cef) < 0.7
    assert parser.detect(b'<14>1 2026-08-30T14:15:30Z SRX-EDGE-01 RT_FLOW - RT_FLOW_SESSION_DENY [junos@2636.1.1.1.2.40]') == 0.0
    print("checkpoint demo: OK", event.fields)


if __name__ == "__main__":
    demo()
