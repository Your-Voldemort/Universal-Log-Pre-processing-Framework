class SchemaDriftFirewall:
    """Field/type-signature check — not ML. Learns each source format's
    signature from the first event seen, then quarantines (never silently
    drops or mis-maps) any event whose fields drift from it."""

    def __init__(self, quarantine_store):
        self._signatures: dict[str, dict[str, type]] = {}
        self._quarantine = quarantine_store

    def check(self, source_format: str, fields: dict) -> dict | None:
        known = self._signatures.setdefault(
            source_format, {k: type(v) for k, v in fields.items()}
        )
        type_drift = {
            k: {"expected": known[k].__name__, "received": type(v).__name__}
            for k, v in fields.items()
            if k in known and type(v) is not known[k]
        }
        new_fields = sorted(set(fields) - set(known))
        if type_drift or new_fields:
            alert = {"source": source_format, "type_drift": type_drift, "new_fields": new_fields}
            self._quarantine.hold(source_format, fields, alert)
            return alert
        return None


def demo():
    from drift.quarantine_store import QuarantineStore

    class FakeQuarantine:
        def __init__(self):
            self.held = []

        def hold(self, source_format, fields, alert):
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

    print("drift firewall demo: OK")


if __name__ == "__main__":
    demo()
