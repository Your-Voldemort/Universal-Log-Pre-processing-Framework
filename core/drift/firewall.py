class SchemaDriftFirewall:
    """Field/type-signature check — not ML. Learns each source format's
    signature from the first event seen, then quarantines (never silently
    drops or mis-maps) any event whose fields drift from it."""

    def __init__(self, quarantine_store):
        self._signatures: dict[str, dict[str, type]] = {}
        self._quarantine = quarantine_store

    def check(
        self, source_format: str, fields: dict, raw_event_id: str | None = None,
        declared_keys: frozenset[str] = frozenset(),
    ) -> dict | None:
        known = self._signatures.setdefault(
            source_format, {k: type(v) for k, v in fields.items()}
        )
        # a key the parser declares but the first event lacked (ports after an ICMP event)
        # is optional, not drift: learn its type the first time it shows up
        for k in set(fields).intersection(declared_keys).difference(known):
            known[k] = type(fields[k])
        type_drift = {
            k: {"expected": known[k].__name__, "received": type(v).__name__}
            for k, v in fields.items()
            if k in known and type(v) is not known[k]
        }
        new_fields = sorted(set(fields) - set(known))
        if type_drift or new_fields:
            alert = {"source": source_format, "type_drift": type_drift, "new_fields": new_fields}
            self._quarantine.hold(source_format, fields, alert, raw_event_id)
            return alert
        return None


def demo():
    from drift.quarantine_store import QuarantineStore

    class FakeQuarantine:
        def __init__(self):
            self.held = []

        def hold(self, source_format, fields, alert, raw_event_id=None):
            self.held.append((source_format, fields, alert))
            return len(self.held)

    fake = FakeQuarantine()
    firewall = SchemaDriftFirewall(fake)

    clean = {"src_ip": "10.10.1.20", "dst_port": 443}
    assert firewall.check("cisco_asa_syslog", clean) is None  # first sighting learns the signature
    assert firewall.check("cisco_asa_syslog", clean) is None  # matches learned signature

    drifted = {"src_ip": "10.10.1.20", "dst_port": "443"}  # int -> str drift
    alert = firewall.check("cisco_asa_syslog", drifted)
    assert alert is not None
    assert alert["type_drift"]["dst_port"] == {"expected": "int", "received": "str"}
    assert len(fake.held) == 1

    new_field = {"src_ip": "10.10.1.20", "dst_port": 443, "vendor_new_field": "x"}
    alert = firewall.check("cisco_asa_syslog", new_field)
    assert alert is not None
    assert alert["new_fields"] == ["vendor_new_field"]
    assert len(fake.held) == 2

    # declared optional keys: a source whose first event lacks ports (ICMP) must not
    # have every later port-bearing event quarantined as "new fields"
    fw = SchemaDriftFirewall(fake)
    declared = frozenset({"src_ip", "dst_port"})
    held_before = len(fake.held)
    assert fw.check("suricata_eve", {"src_ip": "203.0.113.44"}, declared_keys=declared) is None
    assert fw.check("suricata_eve", {"src_ip": "203.0.113.44", "dst_port": 22}, declared_keys=declared) is None
    assert fw.check("suricata_eve", {"src_ip": "203.0.113.44", "dst_port": "22"}, declared_keys=declared) is not None
    alert = fw.check("suricata_eve", {"src_ip": "203.0.113.44", "vendor_new_field": 1}, declared_keys=declared)
    assert alert["new_fields"] == ["vendor_new_field"] and len(fake.held) == held_before + 2

    print("drift firewall demo: OK")


if __name__ == "__main__":
    demo()
