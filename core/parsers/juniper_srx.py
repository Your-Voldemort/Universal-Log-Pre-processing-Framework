import re

from .base import BaseParser, ParsedEvent, iso_to_epoch_ms

# Junos structured-data (RFC 5424) syslog, e.g. `set security log format sd-syslog`:
# <14>1 2026-08-30T19:52:31.123+05:30 SRX-EDGE-01 RT_FLOW - RT_FLOW_SESSION_CREATE [junos@2636.1.1.1.2.40 source-address="10.1.1.10" ...]
RT_FLOW = re.compile(
    r"^<(?P<syslog_pri>\d+)>1 (?P<syslog_timestamp>\S+) (?P<device_name>\S+) (?P<app_name>\S+) "
    r"(?P<proc_id>\S+) RT_FLOW_SESSION_(?P<action>CREATE|CLOSE|DENY) "
    r"\[(?P<sd_id>junos@[\d.]+) (?P<params>.*)\]$"
)
SD_PARAM = re.compile(r'([\w-]+)="((?:[^"\\]|\\.)*)"')

# SD-PARAM -> ULPF field. Every other parameter (NAT, zones, policy, service, application,
# session id, byte counts, close/deny reason) lands in unmapped, never dropped.
KNOWN_PARAMS = {
    "source-address": "src_ip", "destination-address": "dst_ip",
    "source-port": "src_port", "destination-port": "dst_port", "protocol-id": "proto",
}
INT_FIELDS = {"src_port", "dst_port", "proto"}


class JuniperSRXParser(BaseParser):
    source_format = "juniper_srx_rt_flow"
    field_keys = frozenset((*KNOWN_PARAMS.values(), "action", "event_time"))

    def detect(self, raw_bytes: bytes) -> float:
        text = raw_bytes.decode(errors="ignore").strip()
        if RT_FLOW.match(text):
            return 0.95
        # an SRX flow log in a layout this parser doesn't read (e.g. BSD syslog) stays raw
        return 0.5 if "RT_FLOW_SESSION_" in text else 0.0

    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        text = raw_bytes.decode(errors="ignore").strip()
        m = RT_FLOW.match(text)
        if m is None:
            return ParsedEvent(self.source_format, raw_bytes, {}, {"raw_text": text})

        # header parts stay in unmapped verbatim, including the original timestamp text
        unmapped = {k: v for k, v in m.groupdict().items() if k not in ("action", "params")}
        fields: dict = {"action": m["action"].lower()}
        event_time = iso_to_epoch_ms(m["syslog_timestamp"])
        if event_time is not None:
            fields["event_time"] = event_time
        for name, value in SD_PARAM.findall(m["params"]):
            key = KNOWN_PARAMS.get(name)
            if key is None:
                unmapped[name] = value
            else:
                fields[key] = int(value) if key in INT_FIELDS and value.isdigit() else value
        return ParsedEvent(self.source_format, raw_bytes, fields, unmapped)


def demo():
    parser = JuniperSRXParser()
    create = (
        b'<14>1 2026-08-30T19:52:31.123+05:30 SRX-EDGE-01 RT_FLOW - RT_FLOW_SESSION_CREATE '
        b'[junos@2636.1.1.1.2.40 source-address="10.1.1.10" source-port="52341" '
        b'destination-address="198.51.100.30" destination-port="443" connection-tag="0" '
        b'service-name="junos-https" nat-source-address="203.0.113.2" nat-source-port="23456" '
        b'protocol-id="6" policy-name="TRUST-TO-UNTRUST" source-zone-name="trust" '
        b'destination-zone-name="untrust" session-id-32="400123" application="UNKNOWN"]'
    )
    assert parser.detect(create) >= 0.7
    event = parser.parse(create)
    assert event.fields == {
        "action": "create", "event_time": 1788099751123,  # 19:52:31.123 IST = 14:22:31.123 UTC
        "src_ip": "10.1.1.10", "src_port": 52341, "dst_ip": "198.51.100.30", "dst_port": 443, "proto": 6,
    }, event.fields
    assert set(event.fields) <= parser.field_keys
    # lossless: header and every other SD-PARAM kept in unmapped
    assert event.unmapped["device_name"] == "SRX-EDGE-01" and event.unmapped["nat-source-address"] == "203.0.113.2"
    assert event.unmapped["syslog_timestamp"] == "2026-08-30T19:52:31.123+05:30"
    assert event.unmapped["policy-name"] == "TRUST-TO-UNTRUST" and event.unmapped["sd_id"] == "junos@2636.1.1.1.2.40"

    deny = parser.parse(
        b'<14>1 2026-08-30T14:15:30Z SRX-EDGE-01 RT_FLOW - RT_FLOW_SESSION_DENY [junos@2636.1.1.1.2.40 '
        b'source-address="203.0.113.44" source-port="40110" destination-address="10.1.1.10" destination-port="22" '
        b'connection-tag="0" service-name="junos-ssh" protocol-id="6" icmp-type="0" policy-name="UNTRUST-DENY" '
        b'source-zone-name="untrust" destination-zone-name="trust" reason="policy deny"]'
    )
    assert deny.fields["action"] == "deny" and deny.fields["event_time"] == 1788099330000
    assert deny.unmapped["reason"] == "policy deny"

    close = parser.parse(
        b'<14>1 2026-08-30T14:23:22Z SRX-EDGE-01 RT_FLOW - RT_FLOW_SESSION_CLOSE [junos@2636.1.1.1.2.40 '
        b'reason="TCP FIN" source-address="10.1.1.10" source-port="52341" destination-address="198.51.100.30" '
        b'destination-port="443" protocol-id="6" bytes-from-server="48213"]'
    )
    assert close.fields["action"] == "close" and close.unmapped["bytes-from-server"] == "48213"

    bsd = b"<14>Aug 30 14:22:31 SRX-EDGE-01 RT_FLOW: RT_FLOW_SESSION_CREATE: session created 10.1.1.10/52341->198.51.100.30/443"
    assert 0 < parser.detect(bsd) < 0.7  # recognized SRX, unsupported layout: stays raw
    assert parser.detect(b"<166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound TCP") == 0.0
    print("juniper_srx demo: OK", event.fields)


if __name__ == "__main__":
    demo()
