import json

from .base import BaseParser, ParsedEvent, iso_to_epoch_ms

# EVE JSON key -> ULPF field. Everything else in the event (flow counters, app-layer
# records, alert gid/rev/metadata, flow_id, interface, sensor host, the original
# timestamp text) stays in unmapped, nested as Suricata wrote it.
TOP_LEVEL = {"src_ip": "src_ip", "dest_ip": "dst_ip", "src_port": "src_port", "dest_port": "dst_port", "proto": "proto"}
ALERT = {
    "action": "action", "signature": "signature", "signature_id": "signature_id",
    "category": "category", "severity": "severity",
}


def _load(raw_bytes: bytes) -> dict | None:
    text = raw_bytes.decode(errors="ignore").strip()
    if not text.startswith("{"):
        return None
    try:
        doc = json.loads(text)
    except ValueError:
        return None
    return doc if isinstance(doc, dict) and "event_type" in doc and "timestamp" in doc else None


class SuricataEVEParser(BaseParser):
    source_format = "suricata_eve"
    field_keys = frozenset((*TOP_LEVEL.values(), *ALERT.values(), "event_time"))

    def detect(self, raw_bytes: bytes) -> float:
        doc = _load(raw_bytes)
        if doc is None:
            return 0.0
        # a Suricata event that isn't an alert (flow, dns, http, ...) has no finding to map: it stays raw
        return 0.95 if doc["event_type"] == "alert" and isinstance(doc.get("alert"), dict) else 0.5

    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        doc = _load(raw_bytes)
        if doc is None:
            return ParsedEvent(self.source_format, raw_bytes, {}, {"raw_text": raw_bytes.decode(errors="ignore")})

        fields: dict = {}
        event_time = iso_to_epoch_ms(doc["timestamp"])
        if event_time is not None:
            fields["event_time"] = event_time
        for eve_key, key in TOP_LEVEL.items():
            if eve_key in doc:
                fields[key] = doc.pop(eve_key)
        alert = doc["alert"] if isinstance(doc.get("alert"), dict) else {}
        for eve_key, key in ALERT.items():
            if eve_key in alert:
                fields[key] = alert.pop(eve_key)
        if not alert:
            doc.pop("alert", None)
        return ParsedEvent(self.source_format, raw_bytes, fields, doc)


def demo():
    parser = SuricataEVEParser()
    alert = (
        b'{"timestamp":"2026-08-30T19:45:02.123456+0530","flow_id":1234567890123456,"in_iface":"eth0",'
        b'"event_type":"alert","src_ip":"203.0.113.44","src_port":40100,"dest_ip":"172.20.1.8","dest_port":22,'
        b'"proto":"TCP","alert":{"action":"allowed","gid":1,"signature_id":2001219,"rev":20,'
        b'"signature":"ET SCAN Potential SSH Scan","category":"Attempted Information Leak","severity":2},'
        b'"app_proto":"ssh","flow":{"pkts_toserver":1,"bytes_toserver":74},"host":"IDS-SENSOR-01"}'
    )
    assert parser.detect(alert) >= 0.7
    event = parser.parse(alert)
    assert event.fields == {
        "event_time": 1788099302123,  # 14:15:02.123 UTC
        "src_ip": "203.0.113.44", "dst_ip": "172.20.1.8", "src_port": 40100, "dst_port": 22, "proto": "TCP",
        "action": "allowed", "signature": "ET SCAN Potential SSH Scan", "signature_id": 2001219,
        "category": "Attempted Information Leak", "severity": 2,
    }, event.fields
    assert set(event.fields) <= parser.field_keys
    # lossless: everything not extracted stays in unmapped, nested as Suricata wrote it
    assert event.unmapped["timestamp"] == "2026-08-30T19:45:02.123456+0530"
    assert event.unmapped["alert"] == {"gid": 1, "rev": 20}
    assert event.unmapped["flow"]["bytes_toserver"] == 74 and event.unmapped["host"] == "IDS-SENSOR-01"

    icmp = (b'{"timestamp":"2026-08-30T14:14:58Z","event_type":"alert","src_ip":"203.0.113.44",'
            b'"dest_ip":"172.20.1.8","proto":"ICMP","alert":{"action":"allowed","signature_id":2100384,'
            b'"signature":"GPL ICMP_INFO PING","category":"Misc activity","severity":3}}')
    assert parser.detect(icmp) >= 0.7 and "dst_port" not in parser.parse(icmp).fields

    flow = b'{"timestamp":"2026-08-30T14:15:02Z","event_type":"flow","src_ip":"10.0.0.1","dest_ip":"10.0.0.2"}'
    assert 0 < parser.detect(flow) < 0.7  # recognized Suricata, not an alert: stays raw
    assert parser.detect(b"CEF:0|Palo Alto Networks|PAN-OS|11.0.0|traffic|traffic-allow|1|src=1.2.3.4") == 0.0
    assert parser.detect(b"{not json") == 0.0
    print("suricata_eve demo: OK", event.fields)


if __name__ == "__main__":
    demo()
