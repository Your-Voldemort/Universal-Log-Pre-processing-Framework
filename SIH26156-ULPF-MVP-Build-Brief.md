# ULPF — MVP Build Brief for AI Coding Agent

**Project: Universal Log Pre-processing Framework | SIH26156 reference implementation**
**This document is self-contained. You do not need any other file to start building.**

---

## 0. How to use this document

Read this entire document before writing any code. Then:

1. Build in the milestone order given in Section 9. Do not jump to frontend polish before the core pipeline (ingest → parse → map → store) runs end to end with real sample data.
2. Where this document has already made a decision (tech stack, file structure, schema shape), follow it exactly. Do not substitute a different library, database, or repo layout.
3. Where something is genuinely ambiguous and not covered here, make the most reasonable choice, leave a one-line comment explaining the assumption, and keep moving. Only stop and ask if you are genuinely blocked (e.g., a required credential, a decision that would be expensive to reverse).
4. After each milestone, verify it against that milestone's "done when" checkpoint before starting the next one.
5. A working end-to-end pipeline with 1 parser beats a polished single component with nothing connected to it. If you're short on time, cut breadth (fewer formats, simpler UI) before you cut depth (never skip the raw+normalized dual storage or the hash chain — those are the point of the project).

---

## 1. What you're building

A tool that ingests security logs from perimeter network devices (firewalls, routers, IDS/IPS — different vendors, different formats), and converts every log into one standardized format (OCSF — Open Cybersecurity Schema Framework) without ever discarding or silently altering the original data. It must run **completely offline** after initial setup — this is designed for critical-infrastructure environments where sending data to the cloud is not an option. When it encounters a log format it doesn't recognize, a small locally-run AI model proposes a mapping, which a human must approve before it's used — the AI never runs in the live production path.

---

## 2. Non-negotiable constraints

These override any convenient shortcut. Violating any of these means the build has failed its core purpose, even if it demos smoothly.

- **Zero external network calls at runtime.** All dependencies (OCSF schema, AI model weights, npm/pip packages) must be fetched once during setup, not fetched lazily at runtime. The running system must work with the network cable pulled out.
- **Nothing is ever silently dropped or altered.** Every raw log, byte-for-byte, is stored immutably and linked to its normalized output via a hash. Fields that can't be confidently mapped go into an explicit `unmapped` bucket — never discarded.
- **AI proposes, a human approves, production is deterministic.** The AI model only ever drafts a new mapping config file for human review. It is never called during normal ingestion of already-known formats. This is a hard architectural rule, not a performance optimization.
- **Target schema is OCSF, not a custom schema.** Map into the real OCSF taxonomy (class_uid, category_uid, standard attribute names). Don't invent your own field names for concepts OCSF already defines.
- **New format support = new config file, not new code.** Onboarding a new log source should mean adding a YAML mapping file, not editing the core engine.
- **Never claim regulatory compliance.** Any UI text, report, or documentation referencing CERT-In/SEBI/NCIIPC must use this exact framing: *"provides technical controls and evidence that support applicable [regulation] requirements"* — never "makes you compliant" or "ensures compliance."

---

## 3. Tech stack (fixed — do not substitute)

| Layer | Technology |
|---|---|
| Ingestion | Vector (Rust, single binary) — listens on Syslog UDP/TCP 514 and an HTTP endpoint |
| Core engine / API | Python 3.12, FastAPI, Pydantic |
| OCSF validation | `jsonschema` against a locally-vendored copy of the OCSF schema (clone `github.com/ocsf/ocsf-schema` once during setup — do not fetch at runtime) |
| AI-assist | Ollama running locally, model `qwen2.5:3b` or `llama3.2:3b` (pull once during setup) |
| Hash-chain integrity | Python `hashlib` (SHA-256) — no external library needed |
| Raw log store | Flat files, partitioned by date/source, plus a Postgres index table |
| Normalized store | PostgreSQL 16, JSONB column, GIN index for search |
| Compliance reports | Jinja2 templates → Markdown (PDF export optional, not required for MVP) |
| Frontend | React + Vite + TailwindCSS |
| Orchestration | Docker Compose |

---

## 4. Scope — build this, not that

| Build (MVP scope) | Do not build (explicitly out of scope) |
|---|---|
| 2 vendor parsers: Cisco ASA syslog, Palo Alto CEF | Support for every possible log format |
| OCSF mapping for Network Activity (class_uid 4001) only | Full coverage of all ~70 OCSF event classes |
| Hash-chain with a working `verify()` function | Formal cryptographic audit certification |
| AI-assist for exactly 1 demo "unknown format" | Robust handling of arbitrary malformed AI output |
| Postgres storage + basic search UI | Migration tooling to OpenSearch/Parseable (mention only, don't build) |
| Schema drift firewall with quarantine queue | ML-based anomaly detection |
| 1 CERT-In-style incident report template | Multiple regulator profiles (SEBI/RBI) with switching logic |
| Live metrics dashboard (see Section 8.11) | Historical trend charts, multi-day analytics |
| Single-node deployment via Docker Compose | Kubernetes, Helm charts, multi-node clustering |

If you find yourself building anything in the right-hand column, stop — that's scope creep, not the MVP.

---

## 5. System architecture

```
Perimeter device logs (Cisco ASA, Palo Alto, ...)
        │
        ▼
Ingestion layer (Vector — syslog/HTTP listener)
        │
        ▼
Parser registry (detects format, routes)
        │
        ├── confidence ≥ 0.7 ──────────► known parser
        │                                     │
        └── confidence < 0.7 ──► AI-assist ───┘
                                  (proposes mapping,
                                   human approves,
                                   becomes a new
                                   parser)
                                     │
                                     ▼
                          OCSF mapper + hash chain
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                  ▼
             Raw store                          Normalized store
        (hash-chained,                          (OCSF JSON in
         immutable)                              Postgres JSONB)
                    │                                  │
                    │         ┌────────────────────────┤
                    │         ▼                        ▼
                    │   Schema drift firewall    Search & compliance API
                    │   (quarantines anomalies)         │
                    │                                   ▼
                    └──────────────────────────►  Dashboard (React)
```

Every arrow in this diagram must exist as working code by the end of the build — this isn't aspirational, it's the literal MVP.

---

## 6. Repository structure

```
ulpf/
├── docker-compose.yml
├── .env.example
├── README.md
├── vector/
│   └── vector.toml
├── core/
│   ├── main.py
│   ├── requirements.txt
│   ├── parsers/
│   │   ├── base.py                 # BaseParser ABC, ParsedEvent dataclass
│   │   ├── cisco_asa_syslog.py
│   │   ├── paloalto_cef.py
│   │   └── registry.py             # ParserRegistry — detect + route
│   ├── ocsf/
│   │   ├── schema/                 # vendored OCSF schema (git clone, once)
│   │   ├── mapper.py               # applies a mapping YAML to a ParsedEvent
│   │   └── mappings/
│   │       ├── cisco_asa_syslog.yaml
│   │       └── paloalto_cef.yaml
│   ├── storage/
│   │   ├── raw_store.py
│   │   ├── normalized_store.py
│   │   └── hashchain.py
│   ├── ai_assist/
│   │   ├── ollama_client.py
│   │   └── mapping_prompt.py
│   ├── compliance/
│   │   ├── profiles/cert_in.yaml
│   │   └── report_generator.py
│   ├── drift/
│   │   ├── firewall.py
│   │   └── quarantine_store.py
│   └── api/
│       ├── routes_search.py
│       ├── routes_ingest.py
│       ├── routes_compliance.py
│       ├── routes_drift.py
│       └── routes_mapping.py       # AI-assist propose/approve endpoints
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   │       ├── DashboardMetrics.tsx
│   │       ├── SearchTable.tsx
│   │       ├── DriftAlerts.tsx
│   │       ├── MappingReview.tsx
│   │       ├── ComplianceReport.tsx
│   │       └── AirGapDemo.tsx
│   ├── package.json
│   └── vite.config.ts
├── benchmark/
│   └── load_test.py
└── testdata/
    └── sample_logs.txt             # see Section 10 — real sample lines live here
```

---

## 7. Data contracts — build to these exact shapes

### 7.1 `ParsedEvent`
```python
from dataclasses import dataclass

@dataclass
class ParsedEvent:
    source_format: str      # e.g. "cisco_asa_syslog"
    raw_bytes: bytes
    fields: dict             # flat key-value extraction, e.g. {"src_ip": "10.10.1.20"}
    unmapped: dict            # anything not confidently extracted
```

### 7.2 OCSF mapping config (YAML)
```yaml
source_format: cisco_asa_syslog
ocsf_class_uid: 4001          # Network Activity
ocsf_category_uid: 4
field_map:
  src_ip: src_endpoint.ip
  dst_ip: dst_endpoint.ip
  dst_port: dst_endpoint.port
  action: disposition
  proto: connection_info.protocol_name
static_fields:
  metadata.product.name: "Cisco ASA"
  metadata.version: "1.9.0"
unmapped_bucket: "unmapped"
```

### 7.3 Final OCSF output event (exact target shape)
```json
{
  "class_uid": 4001,
  "category_uid": 4,
  "activity_name": "Connection Attempt",
  "metadata": {
    "product": { "name": "Cisco ASA", "vendor_name": "Cisco" },
    "version": "1.9.0"
  },
  "src_endpoint": { "ip": "10.10.1.20" },
  "dst_endpoint": { "ip": "172.16.1.50", "port": 443 },
  "connection_info": { "protocol_name": "tcp" },
  "disposition": "Allowed",
  "observables": [
    { "name": "src_endpoint.ip", "value": "10.10.1.20" },
    { "name": "dst_endpoint.ip", "value": "172.16.1.50" }
  ],
  "unmapped": {
    "vendor_zone": "DMZ-INTERNAL"
  },
  "ulpf": {
    "raw_event_id": "evt_893823",
    "raw_event_hash": "<sha256 hex>",
    "parser_version": "cisco_asa_syslog-1.0.0",
    "mapping_confidence": 0.97
  }
}
```
`ulpf.mapping_confidence` must be the actual float returned by `ParserRegistry.route()` for this event — not a hardcoded or estimated number.

### 7.4 Hash chain record
```python
{
  "event_hash": "<sha256 of raw_bytes>",
  "prev_chain_hash": "<previous record's chain_hash, or 64 zeros for genesis>",
  "chain_hash": "<sha256(prev_chain_hash + event_hash)>"
}
```

### 7.5 Drift alert
```python
{
  "source": "cisco_asa_syslog",
  "type_drift": {"dst_port": {"expected": "int", "received": "str"}},
  "new_fields": ["vendor_new_field"]
}
```

---

## 8. Component specs — interface, acceptance criteria, and example I/O

### 8.1 Ingestion — `vector/vector.toml`
Vector listens on UDP/TCP 514 for syslog and an HTTP endpoint for other formats, forwards raw bytes unmodified to the core API's `/ingest` endpoint (`routes_ingest.py`).
**Done when:** posting a raw log line to Vector's listener results in that exact byte sequence arriving at `/ingest`.

### 8.2 Parser Registry — `core/parsers/base.py`, `registry.py`
```python
from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def detect(self, raw_bytes: bytes) -> float:
        """Confidence 0.0-1.0 that this parser handles the input."""

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        ...

class ParserRegistry:
    def __init__(self):
        self._parsers: list[BaseParser] = []

    def register(self, parser: BaseParser):
        self._parsers.append(parser)

    def route(self, raw_bytes: bytes) -> tuple[BaseParser | None, float]:
        scored = [(p, p.detect(raw_bytes)) for p in self._parsers]
        best = max(scored, key=lambda x: x[1], default=(None, 0.0))
        return best if best[1] >= 0.7 else (None, best[1])
```
**Done when:** feeding the Section 10 sample lines through `route()` returns the correct parser with confidence ≥ 0.7 for both known formats, and returns `(None, <score>)` for the unknown-format sample.

### 8.3 Vendor Parsers — `cisco_asa_syslog.py`, `paloalto_cef.py`
Implement `detect()` and `parse()` for each. Use the exact sample lines and expected extracted fields in Section 10 as your test cases — do not guess the format, build against those literal examples.

### 8.4 OCSF Mapper — `core/ocsf/mapper.py`
Reads a `ParsedEvent` plus the matching mapping YAML (Section 7.2), produces the OCSF JSON shape in Section 7.3. Validate the output against the vendored OCSF JSON schema before returning it.
**Done when:** running the Cisco ASA sample through parse → map produces JSON matching Section 7.3's structure (values will differ based on the actual sample, but the shape — including `unmapped` and `ulpf` blocks — must match exactly).

### 8.5 Hash Chain — `core/storage/hashchain.py`
```python
import hashlib

class HashChain:
    def __init__(self, genesis: str = "0" * 64):
        self._last_hash = genesis

    def append(self, raw_bytes: bytes) -> dict:
        event_hash = hashlib.sha256(raw_bytes).hexdigest()
        chain_hash = hashlib.sha256((self._last_hash + event_hash).encode()).hexdigest()
        record = {"event_hash": event_hash, "prev_chain_hash": self._last_hash, "chain_hash": chain_hash}
        self._last_hash = chain_hash
        return record

    @staticmethod
    def verify(records: list[dict], genesis: str = "0" * 64) -> bool:
        prev = genesis
        for r in records:
            expected = hashlib.sha256((prev + r["event_hash"]).encode()).hexdigest()
            if expected != r["chain_hash"]:
                return False
            prev = r["chain_hash"]
        return True
```
**Done when:** `verify()` returns `True` on an untouched chain of ≥10 appended records, and returns `False` when any single record's `event_hash` is manually edited afterward.

### 8.6 Dual Storage — `raw_store.py`, `normalized_store.py`
Raw store: append raw bytes to a date/source-partitioned file, index `(event_id, file_offset, hash, chain_hash, timestamp, source)` in Postgres. Normalized store: insert the OCSF JSON into a Postgres JSONB column with a GIN index, storing `ulpf.raw_event_id` as a foreign key back to the raw index.
**Done when:** given a `raw_event_id`, you can fetch both the exact original raw bytes and its normalized OCSF record, and they cross-reference each other.

### 8.7 AI-Assist — `ai_assist/mapping_prompt.py`, `ollama_client.py`
```python
MAPPING_PROMPT_TEMPLATE = """You are helping map an unrecognized log format to the OCSF schema.

OCSF Network Activity (class_uid 4001) key fields:
{ocsf_class_schema}

Example mapping for a known format:
{example_mapping_yaml}

New, unrecognized log samples:
{raw_samples}

Propose a YAML field mapping in the same structure as the example above,
mapping fields you can confidently identify. Put anything ambiguous under
"unmapped_bucket". Respond with ONLY the YAML, no explanation."""
```
Call this against `http://localhost:11434/api/generate`. Parse the YAML response, validate its structure, and expose it via `routes_mapping.py` as a **proposal** — it must NOT be written to `ocsf/mappings/` or used by the registry until a human confirms it via the `MappingReview.tsx` UI.
**Done when:** feeding the Section 10 "unknown format" sample produces a syntactically valid mapping YAML proposal, and that proposal only becomes an active parser after an explicit `/approve` API call.

### 8.8 Schema Drift Firewall — `drift/firewall.py`, `quarantine_store.py`
```python
class SchemaDriftFirewall:
    def __init__(self, quarantine_store):
        self._signatures: dict[str, dict[str, type]] = {}
        self._quarantine = quarantine_store

    def check(self, source_format: str, fields: dict) -> dict | None:
        known = self._signatures.setdefault(source_format, {k: type(v) for k, v in fields.items()})
        type_drift = {
            k: {"expected": known[k].__name__, "received": type(v).__name__}
            for k, v in fields.items() if k in known and type(v) is not known[k]
        }
        new_fields = set(fields) - set(known)
        if type_drift or new_fields:
            alert = {"source": source_format, "type_drift": type_drift, "new_fields": list(new_fields)}
            self._quarantine.hold(fields, alert)
            return alert
        return None
```
`quarantine_store.py` needs three operations exposed via `routes_drift.py` matching the UI: **quarantine** (default, keep holding), **auto-fix** (coerce type, log the coercion, allow through), **ignore** (accept once, don't update the signature).
**Done when:** sending a known-format event with an unexpected field type triggers an alert, the event lands in the quarantine table (not the normalized store), and all three UI actions work.

### 8.9 Compliance Report Generator — `compliance/report_generator.py`
```python
INCIDENT_REPORT_FIELDS = [
    "incident_timestamp", "systems_affected", "nature_of_incident",
    "remedial_action_taken", "point_of_contact",
]
```
Render these via Jinja2 from a set of flagged OCSF events. Use the exact safe-framing sentence from Section 2 anywhere this report is labeled.
**Done when:** triggering a report generation for a sample flagged event produces a filled-in Markdown document with all 5 fields populated from real event data (not placeholders).

### 8.10 Search & Compliance API — `api/routes_search.py`
Expose `/search?q=&source=&time_range=` querying the normalized store's JSONB via Postgres full-text search.
**Done when:** searching for a known IP address returns the matching normalized event(s) with sub-second response on the sample dataset.

### 8.11 Dashboard — `frontend/src/components/DashboardMetrics.tsx`
Must show, live: events/sec, normalized %, schema drift count (current session), unmapped-field %, raw preservation % (should read 100%), and per-source health (● healthy / ● drifted, one row per parser). Include an "inject malformed log" button wired directly to the drift firewall for the live demo.
**Done when:** clicking "inject malformed log" visibly flips a source's status to drifted and increments the drift count within 1 second, with the event appearing in the quarantine queue.

---

## 9. Build order / milestones

1. **Scaffold** — repo structure, Docker Compose skeleton (Postgres + empty FastAPI service up and responding to `/health`).
2. **Ingestion + raw storage** — Vector → `/ingest` → raw store + hash chain. Verify with `HashChain.verify()` on a batch of test posts.
3. **Parser registry + 2 vendor parsers** — build against the Section 10 sample lines until `route()` and `parse()` produce the documented expected output.
4. **OCSF mapper** — wire mapping YAMLs, produce valid OCSF JSON (Section 7.3 shape) for both sample formats, validated against the vendored schema.
5. **Normalized storage + search API** — both samples queryable via `/search`.
6. **Schema drift firewall** — inject a type-mismatched version of a sample event, confirm it's quarantined, not silently stored.
7. **AI-assist** — feed the unknown-format sample, get a mapping proposal, manually approve it, confirm the registry now routes that format correctly.
8. **Compliance report generator** — generate one sample report end-to-end.
9. **Frontend** — dashboard first (it's the demo centerpiece), then search table, drift alerts, mapping review, air-gap indicator.
10. **Docker Compose air-gap verification** — set `internal: true` on the network, confirm the full stack still works with zero external calls.
11. **Benchmark script** — run `benchmark/load_test.py` against the running stack, record the real events/sec number.

Do not reorder this list. Steps 2-5 are the actual product; everything after step 5 is differentiation and polish on top of a working core.

---

## 10. Sample test data (`testdata/sample_logs.txt`)

Use these exact lines throughout development and testing — don't substitute invented examples.

**Cisco ASA syslog (known format 1):**
```
<166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound TCP connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) to inside:10.10.1.20/52341 (10.10.1.20/52341)
```
Expected extracted fields: `src_ip=10.10.1.20, dst_ip=172.16.1.50, src_port=52341, dst_port=443, proto=TCP, action=Built` → maps to `disposition=Allowed`.

**Palo Alto CEF (known format 2):**
```
CEF:0|Palo Alto Networks|PAN-OS|11.0.0|traffic|traffic-allow|1|rt=Aug 30 2026 14:22:31 src=10.2.4.21 dst=172.20.1.8 spt=52341 dpt=443 proto=tcp act=allow deviceExternalId=PA-VM-01
```
Expected extracted fields: `src_ip=10.2.4.21, dst_ip=172.20.1.8, src_port=52341, dst_port=443, proto=tcp, action=allow` → maps to `disposition=Allowed`.

**Unknown format (for the AI-assist demo — a FortiGate-style key=value log, intentionally unsupported by any built-in parser):**
```
date=2026-08-30 time=14:22:31 devname="FGT-EDGE-01" logid="0000000013" type="traffic" srcip=10.5.2.14 dstip=203.0.113.44 dstport=8080 proto=6 action="accept" policyid=12
```
This should score below 0.7 confidence on both built-in parsers and route to AI-assist.

**Drift test case:** take the Cisco ASA sample above and manually change the parsed `dst_port` value from an integer to the string `"443"` before it reaches the firewall — this should trigger a type-drift alert.

---

## 11. Definition of done (MVP)

- [ ] Both vendor parsers correctly parse their Section 10 sample lines
- [ ] OCSF mapper output matches the Section 7.3 shape exactly, including `unmapped` and `ulpf` blocks
- [ ] `HashChain.verify()` returns `True` on a clean chain and `False` on a tampered one
- [ ] Raw store and normalized store are cross-referenceable by `raw_event_id`
- [ ] AI-assist produces a mapping proposal for the unknown-format sample, and it only activates after explicit human approval
- [ ] Schema drift firewall quarantines the drift test case instead of storing it normally
- [ ] Search API returns correct results for a known IP
- [ ] One compliance report generates successfully with real field data
- [ ] Dashboard shows live metrics and the "inject malformed log" button works
- [ ] `docker compose up` with `internal: true` networking still runs the full pipeline successfully
- [ ] Benchmark script produces a real, reproducible events/sec number (report whatever it actually is — do not target a specific number)

---

## 12. Demo script

1. `docker compose up` — show the stack starting.
2. Post the Cisco ASA and Palo Alto sample lines — show them appear normalized in the dashboard within seconds.
3. Post the unknown FortiGate-style sample — show it route to AI-assist, show the proposed mapping, approve it, then post it again and show it now parses correctly.
4. Click "inject malformed log" — show the drift firewall catch it and the event land in quarantine, live on the dashboard.
5. Open the raw store and normalized store side by side for one event — show the `raw_event_hash` linking them, and run `HashChain.verify()` live in a terminal.
6. Disconnect the network (or restart with `internal: true`) — show the stack keeps working with zero errors.
7. Generate a compliance report from a flagged event — show the safe-framing language in the output.
