"""End-to-end API tests against a real Postgres: the checks that verified each ULPF
feature as it was built, kept so they can be rerun before a demo.

DESTRUCTIVE: every test TRUNCATEs all ULPF tables in ULPF_TEST_DATABASE_URL and resets
the hash chain. Point it at a throwaway database only (see README, "End-to-end tests"):

    cd core
    ULPF_TEST_DATABASE_URL=postgresql://ulpf:ulpf@localhost:5434/ulpf ../.venv/bin/python tests/test_e2e.py

Plain asserts, no test framework needed; `python -m pytest tests/` works too if pytest
is installed. Ollama isn't needed: AI-assist proposals are stored the way a model
response would be, then approved through the real API.
"""
import atexit
import hashlib
import os
import shutil
import sys
import tempfile
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent
if not os.environ.get("ULPF_TEST_DATABASE_URL"):
    raise SystemExit("Set ULPF_TEST_DATABASE_URL to a throwaway Postgres: these tests TRUNCATE every ULPF table.")

# app modules read these at import time, so they're set before any app import
os.environ["DATABASE_URL"] = os.environ["ULPF_TEST_DATABASE_URL"]
os.environ["ULPF_RAW_DIR"] = tempfile.mkdtemp(prefix="ulpf-test-raw-")
atexit.register(shutil.rmtree, os.environ["ULPF_RAW_DIR"], True)
sys.path.insert(0, str(CORE))

import psycopg  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from ai_assist.proposal_store import ProposalStore  # noqa: E402
from api.routes_mapping import APPROVED_DIR  # noqa: E402
from api.state import state  # noqa: E402
from storage.db import get_conn, init_schema  # noqa: E402
from storage.hashchain import GENESIS  # noqa: E402
from storage.raw_store import RAW_DATA_DIR  # noqa: E402

if APPROVED_DIR.exists() and any(APPROVED_DIR.iterdir()):
    raise SystemExit(f"{APPROVED_DIR} holds approved mappings; move them aside first (the tests approve and remove their own).")


def _lines(name: str) -> list[bytes]:
    path = CORE.parent / "testdata" / name
    return [line.strip() for line in path.read_bytes().splitlines() if line.strip() and not line.startswith(b"#")]


CISCO, PALO, FORTI = _lines("sample_logs.txt")
DEMO = _lines("demo_logs.txt")
ASA = b"<166>Aug 30 2026 14:22:31 ASA-FW01 : "
FORTI_YAML = (
    "source_format: {name}\nocsf_class_uid: 4001\nocsf_category_uid: 4\nfield_map:\n"
    "  srcip: src_endpoint.ip\n  dstip: dst_endpoint.ip\n  dstport: dst_endpoint.port\n  action: disposition\n"
)


@contextmanager
def fresh_client():
    """Empty tables, raw store and approved/ dir, then app startup: registry, mapper,
    drift signatures and chain head are all rebuilt from that clean state."""
    init_schema()
    with get_conn() as conn:
        conn.execute("TRUNCATE normalized_events, quarantine_events, mapping_proposals, raw_events RESTART IDENTITY")
        conn.execute("UPDATE chain_state SET last_hash = %s WHERE id = 1", (GENESIS,))
    shutil.rmtree(RAW_DATA_DIR, ignore_errors=True)
    shutil.rmtree(APPROVED_DIR, ignore_errors=True)
    try:
        with TestClient(main.app) as client:
            yield client
    finally:
        shutil.rmtree(APPROVED_DIR, ignore_errors=True)


def ingest(c, line: bytes) -> dict:
    return c.post("/ingest", content=line).json()


def ingest_demo(c) -> None:
    for line in DEMO:
        ingest(c, line)


def search(c, **params) -> list[dict]:
    r = c.get("/search", params=params)
    assert r.status_code == 200, r.text
    return r.json()["results"]


def verified(c) -> bool:
    return c.get("/verify-chain").json()["verified"]


def raw_row_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT count(*) FROM raw_events").fetchone()[0]


def propose(name: str) -> int:
    return ProposalStore().create(name, FORTI_YAML.format(name=name), FORTI.decode())


def resolve(c, item_id: int, action: str):
    return c.post(f"/drift/quarantine/{item_id}/resolve", json={"action": action})


def inject(c) -> tuple[str, int]:
    """The dashboard's drift demo button; returns (raw_event_id, quarantine item id)."""
    r = c.post("/drift/inject-malformed").json()
    assert r["status"] == "quarantined", r
    assert r["alert"]["type_drift"]["dst_port"] == {"expected": "int", "received": "str"}, r
    item = next(i for i in c.get("/drift/quarantine").json() if i["raw_event_id"] == r["event_id"])
    return r["event_id"], item["id"]


# --- ingestion and parsing -----------------------------------------------------------

def test_demo_dataset_normalizes_every_built_in_format():
    with fresh_client() as c:
        statuses = Counter(ingest(c, line)["status"] for line in DEMO)
        unknown = sum(line.startswith(b"date=") for line in DEMO)  # FortiGate: the AI-assist demo's format
        # Suricata and Check Point lead with port-less ICMP events: no false drift on later ones
        assert statuses == {"ok": len(DEMO) - unknown, "unknown_format": unknown}, statuses
        m = c.get("/metrics").json()
        assert m["normalized_by_source"] == {
            "cisco_asa_syslog": 22, "paloalto_cef": 26, "juniper_srx_rt_flow": 5,
            "suricata_eve": 4, "checkpoint_log_exporter": 4,
        }, m
        assert m["drift_by_source"] == {} and m["chain_verified"] is True, m


def test_events_keep_their_own_time_and_everything_unmapped():
    with fresh_client() as c:
        cisco = ingest(c, CISCO)["ocsf_event"]
        assert cisco["time"] == 1788099751000 and cisco["src_endpoint"] == {"ip": "10.10.1.20", "port": 52341}
        assert cisco["connection_info"]["protocol_name"] == "tcp" and cisco["disposition"] == "Allowed"
        assert cisco["unmapped"]["device_name"] == "ASA-FW01" and cisco["unmapped"]["src_zone"] == "inside"

        palo = ingest(c, PALO)["ocsf_event"]
        assert palo["time"] == 1788099751000 and palo["unmapped"]["rt"] == "Aug 30 2026 14:22:31"

        deny = ingest(c, ASA + b'%ASA-4-106023: Deny tcp src outside:203.0.113.44/40100 dst inside:10.10.1.20/22 '
                               b'by access-group "OUTSIDE_IN" [0x0, 0x0]')
        assert deny["ocsf_event"]["disposition"] == "Denied", deny
        teardown = ingest(c, ASA + b"%ASA-6-302014: Teardown TCP connection 8847123 for outside:172.16.1.50/443 "
                                   b"to inside:10.10.1.20/52341 duration 0:01:02 bytes 5120 TCP FINs")
        assert teardown["ocsf_event"]["disposition"] == "Allowed", teardown


def test_unsupported_layouts_stay_raw_as_unknown_format():
    expected_confidence = {
        ASA + b"%ASA-6-305011: Built dynamic TCP translation from inside:10.10.1.20/52341 to outside:203.0.113.10/52341": 0.5,
        b'{"timestamp":"2026-08-30T14:15:02Z","event_type":"flow","src_ip":"10.0.0.1","dest_ip":"10.0.0.2"}': 0.5,
        b"<14>Aug 30 14:22:31 SRX-EDGE-01 RT_FLOW: RT_FLOW_SESSION_CREATE: session created 10.1.1.10/52341->198.51.100.30/443": 0.5,
        b'<134>1 2026-08-30T14:15:30Z CP-GW-DC2 CheckPoint 26203 - [action:"Detect"; product:"IPS"; '
        b'src:"203.0.113.44"; dst:"10.1.2.5"]': 0.5,
        b"CEF:0|Check Point|VPN-1 & FireWall-1|Check Point|Accept|https|Unknown|act=Accept src=10.1.2.20": 0.5,
        FORTI: 0.0,  # the Build Brief's AI-assist demo line must stay unrecognized
    }
    with fresh_client() as c:
        for line, confidence in expected_confidence.items():
            r = ingest(c, line)
            assert r["status"] == "unknown_format" and r["confidence"] == confidence, (line, r)
        assert raw_row_count() == len(expected_confidence)  # raw bytes kept for every one
        assert verified(c)


def test_juniper_suricata_checkpoint_event_shapes_and_drift():
    with fresh_client() as c:
        ingest_demo(c)

        srx = search(c, source="juniper_srx_rt_flow")
        assert {e["dst_endpoint"]["port"] for e in srx if e["disposition"] == "Denied"} == {22, 3389}
        dns = next(e for e in srx if e["dst_endpoint"]["port"] == 53)
        assert dns["connection_info"]["protocol_name"] == "udp" and dns["unmapped"]["nat-source-address"] == "203.0.113.2"

        ids = search(c, source="suricata_eve")
        icmp = next(e for e in ids if e["finding_info"]["uid"] == "2100384")
        assert icmp["class_uid"] == 2004 and icmp["severity_id"] == 2 and icmp["disposition"] == "Detected"
        assert "port" not in icmp["evidences"][0]["dst_endpoint"]
        mssql = next(e for e in ids if e["finding_info"]["uid"] == "2010935")
        assert mssql["severity_id"] == 3 and mssql["evidences"][0]["dst_endpoint"] == {"ip": "172.20.1.8", "port": 1433}
        assert mssql["time"] == 1788099310401 and mssql["unmapped"]["flow"]["bytes_toserver"] == 74

        cp = search(c, source="checkpoint_log_exporter")
        reject = next(e for e in cp if e["unmapped"]["rule_name"] == "Block direct SMTP")
        assert reject["disposition"] == "Denied" and reject["dst_endpoint"] == {"ip": "198.51.100.66", "port": 25}
        accept = next(e for e in cp if e["disposition"] == "Allowed")
        assert accept["time"] == 1788098710000 and accept["unmapped"]["xlatesrc"] == "203.0.113.9"

        # real type drift on the newer sources is still caught
        alert = next(line for line in DEMO if b'"dest_port":1433' in line)
        r = ingest(c, alert.replace(b'"dest_port":1433', b'"dest_port":"1433"'))
        assert r["status"] == "quarantined", r
        assert r["alert"]["type_drift"]["dst_port"] == {"expected": "int", "received": "str"}, r
        cp_accept = next(line for line in DEMO if b'action:"Accept"' in line)
        assert ingest(c, cp_accept.replace(b'service:"443"', b'service:"https"'))["status"] == "quarantined"
        assert c.get("/metrics").json()["drift_by_source"] == {"suricata_eve": 1, "checkpoint_log_exporter": 1}


# --- search, dashboard, compliance ----------------------------------------------------

def test_per_source_drift_counts_and_time_range_search():
    with fresh_client() as c:
        ingest_demo(c)
        inject(c)
        assert c.get("/metrics").json()["drift_by_source"] == {"cisco_asa_syslog": 1}

        def count(**params) -> int:
            return len(search(c, **params))

        assert count(time_range="2026-08-30T14:15:00Z/2026-08-30T14:15:10Z") == 5  # PA probe :01 :05 :06 :08 :10
        assert count(time_range="2026-08-30T19:45+05:30/2026-08-30T19:45:10+05:30") == 5  # same window, IST offset
        assert count(source="cisco_asa_syslog", time_range="2026-08-30T14:12Z/2026-08-30T14:13Z") == 4  # ASA denies
        assert count(source="paloalto_cef", time_range="2026-08-30T14:12Z/2026-08-30T14:13Z") == 0
        assert count(time_range="2026-08-30T14:15:20Z/") == 3  # open end: CP :21, PA :23 :25
        assert count(q="203.0.113.44", time_range="/2026-08-30T14:15:05Z") == 4  # open start, combined with text
        window = search(c, time_range="2026-08-30T14:15:10Z/2026-08-30T14:15:15Z")
        assert sorted(e["metadata"]["product"]["name"] for e in window) == (
            ["Junos OS (SRX)"] * 2 + ["PAN-OS"] * 2 + ["Suricata"] * 2), window
        assert c.get("/search", params={"time_range": "yesterday"}).status_code == 422


def test_compliance_report_is_built_from_event_data():
    with fresh_client() as c:
        ingest_demo(c)
        scanner = search(c, q="203.0.113.44")
        assert len(scanner) == 18, len(scanner)
        ids = [e["ulpf"]["raw_event_id"] for e in scanner]
        report = c.post("/compliance/report", json={"raw_event_ids": ids}).json()["report_markdown"]
        for expected in (
            "ULPF provides technical controls and evidence that support applicable CERT-In/SEBI/NCIIPC requirements.",
            "| Incident Timestamp | 2026-08-30 14:14:58 UTC to 2026-08-30 14:15:25 UTC |",
            "| Systems Affected | 10.1.1.10, 10.1.2.5, 172.20.1.8 |",
            "18 event(s) (14 Denied, 4 Detected)",
            "14 event(s) blocked at the perimeter by Check Point Firewall, Junos OS (SRX), PAN-OS",
            "4 event(s) not blocked by the device, pending SOC review",
            "consistent with port scanning",
        ):
            assert expected in report, (expected, report)
        assert "quarantined" not in report and "Certified" not in report


# --- schema drift firewall -------------------------------------------------------------

def test_drift_quarantine_auto_fix_and_ignore():
    with fresh_client() as c:
        assert ingest(c, CISCO)["status"] == "ok"
        raw_id, qid = inject(c)
        assert resolve(c, qid, "quarantine").json()["status"] == "held"
        assert c.get(f"/events/{raw_id}").json()["ocsf_event"] is None  # held, not normalized
        assert c.get("/metrics").json()["drift_count"] == 1

        assert resolve(c, qid, "auto-fix").json()["status"] == "released"
        event = c.get(f"/events/{raw_id}").json()
        assert event["ocsf_event"]["dst_endpoint"]["port"] == 443 and event["raw_log"].startswith("<166>")
        assert event["ocsf_event"]["ulpf"]["drift_resolution"] == {
            "action": "auto-fix", "coerced": {"dst_port": {"from": "str", "to": "int"}}}
        assert c.get("/metrics").json()["drift_count"] == 0
        assert resolve(c, qid, "ignore").status_code == 409  # already resolved

        raw_id2, qid2 = inject(c)
        assert resolve(c, qid2, "ignore").json()["status"] == "released"
        assert c.get(f"/events/{raw_id2}").json()["ocsf_event"]["ulpf"]["drift_resolution"] == {"action": "ignore"}
        inject(c)  # ignore didn't teach the firewall that a string port is fine

        assert resolve(c, qid2, "bogus").status_code == 422
        assert resolve(c, 999999, "auto-fix").status_code == 404
        bad_raw, _ = inject(c)
        lossy = state.quarantine_store.hold(
            "cisco_asa_syslog", {"dst_port": "abc"},
            {"type_drift": {"dst_port": {"expected": "int", "received": "str"}}, "new_fields": []}, bad_raw)
        assert resolve(c, lossy, "auto-fix").status_code == 422
        assert state.quarantine_store.get(lossy)["status"] == "quarantine"
        no_raw_link = state.quarantine_store.hold("cisco_asa_syslog", {}, {"type_drift": {}, "new_fields": []})
        assert resolve(c, no_raw_link, "auto-fix").status_code == 409
        assert verified(c)


# --- AI-assist approval and replay -----------------------------------------------------

def test_mapping_approval_guards_and_restart():
    builtin_cisco = (CORE / "ocsf" / "mappings" / "cisco_asa_syslog.yaml").read_text()
    with fresh_client() as c:
        for bad_name in ("../../parsers/evil", "a/b"):  # source_format becomes a filename
            assert c.post(f"/mapping/{propose(bad_name)}/approve").status_code == 422
        assert not APPROVED_DIR.exists() and not (CORE / "ocsf" / "parsers").exists()
        assert c.post(f"/mapping/{propose('cisco_asa_syslog')}/approve").status_code == 409  # built-in name
        assert (CORE / "ocsf" / "mappings" / "cisco_asa_syslog.yaml").read_text() == builtin_cisco

        assert ingest(c, FORTI)["status"] == "unknown_format"
        pid = propose("fortigate_kv")
        with ThreadPoolExecutor(2) as pool:  # a double-clicked Approve
            codes = sorted(f.result().status_code for f in [pool.submit(c.post, f"/mapping/{pid}/approve") for _ in range(2)])
        assert codes == [200, 409], codes
        assert sum(p.source_format == "fortigate_kv" for p in state.registry._parsers) == 1
        assert c.post(f"/mapping/{propose('fortigate_kv')}/approve").status_code == 409  # name already active
        assert ingest(c, FORTI)["status"] == "ok"

        rejected = propose("fortigate_kv_v2")
        assert c.post(f"/mapping/{rejected}/reject").json() == {"status": "rejected", "id": rejected}
        assert c.post(f"/mapping/{rejected}/reject").status_code == 409
        assert c.post(f"/mapping/{rejected}/approve").status_code == 409
        assert c.post("/mapping/999999/approve").status_code == 404

        with TestClient(main.app) as restarted:  # startup again: registry and mapper rebuilt from disk
            r = ingest(restarted, FORTI)
            assert r["status"] == "ok" and r["ocsf_event"]["dst_endpoint"]["port"] == 8080, r


def test_replay_normalizes_events_stored_before_approval():
    with fresh_client() as c:
        forti_ids = [ingest(c, line)["event_id"] for line in DEMO if line.startswith(b"date=")]
        drift_id = ingest(c, FORTI.replace(b"dstport=8080", b"dstport=http"))["event_id"]
        other_id = ingest(c, b"some other unknown device log")["event_id"]
        assert c.post("/ingest/replay").json() == {
            "normalized": 0, "quarantined": 0, "still_unrecognized": 5, "failed_validation": 0}

        rows_before = raw_row_count()
        r = c.post(f"/mapping/{propose('fortigate_kv')}/approve").json()
        assert r["replayed"] == {"normalized": 3, "quarantined": 1, "still_unrecognized": 1, "failed_validation": 0}, r
        assert raw_row_count() == rows_before and verified(c)  # replay never appends to the raw store or chain

        event = c.get(f"/events/{forti_ids[0]}").json()
        assert event["raw_log"].startswith("date=") and event["ocsf_event"]["ulpf"]["raw_event_id"] == forti_ids[0]
        assert event["ocsf_event"]["ulpf"]["mapping_confidence"] == 1.0

        def held() -> list[dict]:
            return [i for i in c.get("/drift/quarantine").json() if i["raw_event_id"] == drift_id]

        assert len(held()) == 1 and held()[0]["alert"]["type_drift"]["dstport"] == {"expected": "int", "received": "str"}
        assert c.post("/ingest/replay").json() == {  # idempotent
            "normalized": 0, "quarantined": 0, "still_unrecognized": 1, "failed_validation": 0}
        assert len(held()) == 1 and c.get(f"/events/{other_id}").json()["ocsf_event"] is None


# --- hash chain ---------------------------------------------------------------------------

def test_verify_chain_rehashes_raw_bytes_on_disk():
    with fresh_client() as c:
        ids = [ingest(c, line)["event_id"] for line in (CISCO, PALO, FORTI)]
        assert verified(c) and c.get("/metrics").json()["chain_verified"] is True
        with get_conn() as conn:
            rel_path, offset, length = conn.execute(
                "SELECT file_path, file_offset, byte_length FROM raw_events WHERE event_id = %s", (ids[0],)).fetchone()
        log = RAW_DATA_DIR / rel_path
        original = log.read_bytes()
        edited = bytearray(original)
        edited[offset] ^= 0x01  # flip one bit of the first raw event

        log.write_bytes(bytes(edited))
        assert verified(c) is False
        assert c.get("/metrics").json()["chain_verified"] is False  # /verify-chain refreshed the dashboard's cache
        log.write_bytes(original[:offset + length - 3])
        assert verified(c) is False  # truncated
        log.unlink()
        assert verified(c) is False  # deleted: False, not a 500
        log.write_bytes(original)
        assert verified(c) is True

        log.write_bytes(bytes(edited))
        assert state.raw_store.verify_chain_cached(max_age_seconds=3600) is True  # within max age: no re-hash
        assert state.raw_store.verify_chain_cached(max_age_seconds=0) is False
        log.write_bytes(original)

        with get_conn() as conn:
            conn.execute("UPDATE raw_events SET event_hash = repeat('0', 64) WHERE event_id = %s", (ids[1],))
        assert verified(c) is False  # an edited DB row is still caught


def test_chain_writes_are_atomic_and_verification_follows_links():
    with fresh_client() as c:
        ids = [ingest(c, line)["event_id"] for line in (CISCO, b"unrecognized middle line", PALO)]
        assert verified(c)

        with get_conn() as conn:  # make the chain-head update fail after the index row insert
            head = conn.execute("SELECT last_hash FROM chain_state WHERE id = 1").fetchone()[0]
            next_head = hashlib.sha256((head + hashlib.sha256(CISCO).hexdigest()).encode()).hexdigest()
            conn.execute(f"ALTER TABLE chain_state ADD CONSTRAINT test_block_next_head CHECK (last_hash <> '{next_head}')")
        try:
            ingest(c, CISCO)
            raise AssertionError("the chain head update should have failed")
        except psycopg.errors.CheckViolation:
            pass
        finally:
            with get_conn() as conn:
                conn.execute("ALTER TABLE chain_state DROP CONSTRAINT IF EXISTS test_block_next_head")
        with get_conn() as conn:
            orphans = conn.execute("SELECT count(*) FROM raw_events WHERE chain_hash = %s", (next_head,)).fetchone()[0]
        assert orphans == 0, "the index row must roll back with the failed head update"
        assert ingest(c, PALO)["status"] == "ok" and verified(c)  # in-memory head never advanced

        with get_conn() as conn:  # a skewed clock doesn't look like tampering
            conn.execute("UPDATE raw_events SET ingested_at = now() + interval '1 day' WHERE event_id = %s", (ids[0],))
        assert verified(c)

        with TestClient(main.app) as restarted:  # head reloads from chain_state and the chain keeps extending
            assert ingest(restarted, CISCO)["status"] == "ok" and verified(restarted)


def test_deleted_events_break_verification():
    for position in ("middle", "newest"):
        with fresh_client() as c:
            ids = [ingest(c, f"unrecognized line {i}".encode())["event_id"] for i in range(3)]
            assert verified(c)
            with get_conn() as conn:
                conn.execute("DELETE FROM raw_events WHERE event_id = %s", (ids[1] if position == "middle" else ids[-1],))
            assert verified(c) is False, position


if __name__ == "__main__":
    tests = [fn for name, fn in list(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {test.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
