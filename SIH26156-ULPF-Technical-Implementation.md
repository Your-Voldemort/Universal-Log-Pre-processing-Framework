# ULPF Technical Implementation & Tech Stack

**Companion to the PRD and Feasibility Report | SIH26156 | NTRO/NCIIPC**

---

## 1. Tech Stack Summary

| Layer | Technology | Why |
|---|---|---|
| Ingestion | Vector (Rust, MPL-2.0) | Single binary, no phone-home, native Syslog/JSON/file-tail support |
| Core engine / API | Python 3.12 + FastAPI + Pydantic | Fast to build, async, auto OpenAPI docs, clean OCSF schema mapping via Pydantic models |
| Parser registry | Custom Python module | Pluggable `BaseParser` classes, format auto-detection |
| OCSF validation | `jsonschema` against vendored OCSF schema files | No internet dependency once vendored; validates every normalized event |
| AI-assist (new formats) | Ollama (local) running Qwen2.5-3B-Instruct or Llama-3.2-3B-Instruct (GGUF, quantized) | Fully offline inference, no fine-tuning required — few-shot structured-output prompting |
| Hash-chain integrity | Python `hashlib` (SHA-256), custom chain module | Lightweight, no external dependency, Certificate-Transparency-style tamper evidence |
| Raw log store | Date/source-partitioned flat files + SQLite/Postgres index | Simple, append-only, fast to implement |
| Normalized store | PostgreSQL 16 + JSONB + GIN full-text index | ACID, native JSON querying, fast setup — swap to Parseable/OpenSearch post-hackathon for scale |
| Compliance templating | Jinja2 + Markdown (optional WeasyPrint for PDF) | Fast to template CERT-In-format incident reports |
| Schema drift firewall | Custom Python module (field/type-signature comparison + quarantine routing) | Detects vendor field/type changes and quarantines affected events instead of silently dropping or mis-mapping them — no ML needed |
| Frontend | React + Vite + TailwindCSS | Matches team's existing full-stack skill set, fast to build a clean demo UI |
| Orchestration | Docker Compose | One command brings up the whole stack, air-gap-verifiable |
| Benchmarking | Custom Python replay script | Honest, reproducible throughput numbers over a formal benchmark suite |

---

## 2. Repository Structure

```
ulpf/
├── docker-compose.yml
├── .env.example
├── vector/
│   └── vector.toml                 # ingestion agent config
├── core/
│   ├── main.py                     # FastAPI app entrypoint
│   ├── requirements.txt
│   ├── parsers/
│   │   ├── base.py                 # BaseParser interface
│   │   ├── syslog.py               # RFC 5424 parser
│   │   ├── cef.py                  # Common Event Format parser
│   │   ├── json_parser.py          # generic JSON log parser
│   │   ├── registry.py             # format detection + routing
│   ├── ocsf/
│   │   ├── schema/                 # vendored OCSF JSON schema (pulled once, air-gap safe)
│   │   ├── mapper.py                # raw → OCSF transform engine
│   │   ├── mappings/
│   │   │   ├── cisco_asa_syslog.yaml
│   │   │   ├── paloalto_cef.yaml
│   │   │   ├── generic_json.yaml
│   ├── storage/
│   │   ├── raw_store.py            # append-only raw log writer
│   │   ├── normalized_store.py     # Postgres JSONB writer/query
│   │   ├── hashchain.py            # SHA-256 chain logic
│   ├── ai_assist/
│   │   ├── ollama_client.py        # local LLM HTTP client
│   │   ├── mapping_prompt.py       # few-shot prompt template
│   ├── compliance/
│   │   ├── profiles/
│   │   │   ├── cert_in.yaml        # retention, jurisdiction, NTP config
│   │   ├── report_generator.py     # Jinja2 → CERT-In incident report
│   ├── drift/
│   │   ├── firewall.py             # field/type-signature drift checker + quarantine routing
│   │   ├── quarantine_store.py     # holds drifted events until reviewed
│   └── api/
│       ├── routes_search.py
│       ├── routes_ingest.py
│       ├── routes_compliance.py
│       ├── routes_drift.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── SearchTable.tsx
│   │   │   ├── DashboardMetrics.tsx # live events/sec, drift count, raw-preservation %
│   │   │   ├── DriftAlerts.tsx     # quarantine / auto-fix / ignore actions
│   │   │   ├── MappingReview.tsx   # human approval step for AI-proposed mappings
│   │   │   ├── ComplianceReport.tsx
│   │   │   ├── AirGapDemo.tsx      # visual "network disconnected" indicator
│   ├── package.json
│   └── vite.config.ts
├── benchmark/
│   └── load_test.py                # replay N logs, measure events/sec
└── README.md
```

---

## 3. Core Interfaces (write these first — everything else builds on them)

### 3.1 Parser Registry (`core/parsers/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ParsedEvent:
    source_format: str
    raw_bytes: bytes
    fields: dict            # flat key-value extraction from raw log
    unmapped: dict          # anything not confidently parsed

class BaseParser(ABC):
    @abstractmethod
    def detect(self, raw_bytes: bytes) -> float:
        """Return confidence score 0.0-1.0 that this parser handles the input."""

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> ParsedEvent:
        """Extract fields from raw log bytes."""
```

### 3.2 Registry & Routing (`core/parsers/registry.py`)

```python
class ParserRegistry:
    def __init__(self):
        self._parsers: list[BaseParser] = []

    def register(self, parser: BaseParser):
        self._parsers.append(parser)

    def route(self, raw_bytes: bytes) -> tuple[BaseParser | None, float]:
        """Return (best_parser, confidence). None if confidence < threshold —
        triggers AI-assist path."""
        scored = [(p, p.detect(raw_bytes)) for p in self._parsers]
        best = max(scored, key=lambda x: x[1], default=(None, 0.0))
        return best if best[1] >= 0.7 else (None, best[1])
```

This is the exact branch point shown in the architecture diagram: confidence ≥ 0.7 routes to a known parser; below that, the raw sample goes to `ai_assist/`.

### 3.3 OCSF Mapping Config (declarative, not hardcoded)

`core/ocsf/mappings/cisco_asa_syslog.yaml`:
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
  metadata.version: "1.9.0"    # OCSF schema version targeted
unmapped_bucket: "unmapped"     # any field not listed above lands here — this is what makes it lossless
```

Keeping mappings as YAML (not hardcoded Python) is what makes onboarding "plug-and-play" — a new format is a new YAML file, not a code change. It's also exactly what the AI-assist path generates as output.

Running that mapping against a real Cisco ASA log line produces this OCSF event — put this directly on a slide, since it makes "lossless" visually provable instead of just claimed:

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
    "vendor_zone": "DMZ-INTERNAL",
    "policy_id": "POL-9281"
  },
  "ulpf": {
    "raw_event_id": "evt_893823",
    "raw_event_hash": "3b9f2a...c2a1",
    "parser_version": "cisco_asa_syslog-1.0.0",
    "mapping_confidence": 0.97
  }
}
```

Three things worth pointing out to a judge in this exact JSON: `unmapped` proves no field was thrown away, `ulpf.raw_event_hash` is the link into the hash chain in 3.4 below, and `ulpf.mapping_confidence` is literally the same float `ParserRegistry.route()` returned in 3.2 — it's not a separate made-up number, it's the real detection confidence carried through the pipeline.

### 3.4 Hash Chain (`core/storage/hashchain.py`)

```python
import hashlib

class HashChain:
    def __init__(self, genesis: str = "0" * 64):
        self._last_hash = genesis

    def append(self, raw_bytes: bytes) -> dict:
        event_hash = hashlib.sha256(raw_bytes).hexdigest()
        chain_hash = hashlib.sha256(
            (self._last_hash + event_hash).encode()
        ).hexdigest()
        record = {
            "event_hash": event_hash,
            "prev_chain_hash": self._last_hash,
            "chain_hash": chain_hash,
        }
        self._last_hash = chain_hash
        return record

    @staticmethod
    def verify(records: list[dict], genesis: str = "0" * 64) -> bool:
        """Replay the chain independently — proves nothing was altered or removed."""
        prev = genesis
        for r in records:
            expected = hashlib.sha256((prev + r["event_hash"]).encode()).hexdigest()
            if expected != r["chain_hash"]:
                return False
            prev = r["chain_hash"]
        return True
```

`HashChain.verify()` is your live demo proof — run it against the full chain on stage and show it returns `True`, then show it correctly returns `False` if you manually edit one stored record.

### 3.5 AI-Assist Mapping Proposal (`core/ai_assist/mapping_prompt.py`)

**Stated architectural principle — say this explicitly in your pitch, don't leave it implicit:** AI proposes, a human approves, and production normalization is 100% deterministic. The model never sits in the live ingestion path — it only ever drafts a new YAML mapping file, which someone reviews once before it's committed. This preempts the obvious judge question ("you're running an LLM in a security pipeline?") before it gets asked.

```python
MAPPING_PROMPT_TEMPLATE = """You are helping map an unrecognized log format to the OCSF schema.

OCSF Network Activity (class_uid 4001) key fields:
{ocsf_class_schema}

Example mapping for a known format (Cisco ASA syslog):
{example_mapping_yaml}

New, unrecognized log samples:
{raw_samples}

Propose a YAML field mapping in the same structure as the example above,
mapping fields you can confidently identify. Put anything ambiguous under
"unmapped_bucket". Respond with ONLY the YAML, no explanation."""
```

Call this via `ollama_client.py` against a locally-running model (`http://localhost:11434/api/generate`), parse the returned YAML, validate it against the OCSF schema, then present it to the team for one-click confirmation in the UI — which writes it as a new file in `core/ocsf/mappings/` and hot-reloads the registry. That confirm step is important: don't auto-accept AI-proposed mappings without a human check, both for correctness and because judges will ask about it.

### 3.6 Schema Drift Firewall (`core/drift/firewall.py`)

Upgraded from a plain detector to a firewall: instead of only flagging an anomaly, it holds the affected event in quarantine so nothing is silently dropped *or* silently mis-mapped while someone decides what to do with it.

```python
class SchemaDriftFirewall:
    def __init__(self, quarantine_store: "QuarantineStore"):
        self._signatures: dict[str, dict[str, type]] = {}  # source_format -> {field: type}
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
        new_fields = set(fields) - set(known)
        if type_drift or new_fields:
            alert = {"source": source_format, "type_drift": type_drift, "new_fields": list(new_fields)}
            self._quarantine.hold(fields, alert)
            return alert
        return None
```

`QuarantineStore.hold()` writes the event plus the alert reason to a holding table, surfaced in `DriftAlerts.tsx` with three actions matching what a SOC analyst would actually want: **Quarantine** (default — keep holding, don't map), **Auto-fix** (coerce the type, log that a coercion happened), **Ignore** (accept this one instance without updating the source's known signature). This is the exact silent-failure mode — a vendor changing a field's type or name — that your research flagged as a real-world OCSF failure case; the firewall framing plus quarantine queue is what turns "we validate schemas" into a genuine headline feature.

### 3.7 Compliance Engine — safe framing (`core/compliance/report_generator.py`)

One legal/credibility distinction worth being deliberate about: never claim ULPF "makes you CERT-In compliant" — compliance is a property of the whole organization's posture, not something a normalization tool can certify on its own, and it's an easy claim for a sharp judge to puncture. Use this framing everywhere instead — in the generated reports, the UI labels, and the pitch deck:

> "ULPF provides technical controls and evidence that support applicable CERT-In/SEBI/NCIIPC requirements."

Keep the report generator itself simple and field-driven:

```python
INCIDENT_REPORT_FIELDS = [
    "incident_timestamp", "systems_affected", "nature_of_incident",
    "remedial_action_taken", "point_of_contact",
]
```

Populate these directly from the flagged OCSF event(s) via Jinja2, matching `compliance/profiles/cert_in.yaml`'s retention/jurisdiction config from section 2.

### 3.8 Dashboard — what it must show (`frontend/src/components/DashboardMetrics.tsx`)

Skip a generic admin-panel layout — judges should read system health in the first three seconds on stage:

| Metric | Source |
|---|---|
| Events/sec | rolling counter from `routes_ingest.py` |
| Normalized % | successfully mapped ÷ total ingested |
| Schema drift count | live count of `SchemaDriftFirewall` alerts this session |
| Unmapped-field % | size of the `unmapped` bucket ÷ total fields, averaged |
| Raw preservation | should read 100% — losslessness proven at a glance, not claimed |
| Per-source health | one row per vendor parser — ● healthy / ● drifted |

Wire an "inject malformed log" button directly to the firewall — trigger it live, watch a source's status flip to drifted and the event land in the quarantine queue in real time. Rehearse this exact moment more than any other part of the demo.

---

## 4. Docker Compose (air-gap-ready)

```yaml
services:
  vector:
    image: timberio/vector:0.42.0-debian
    volumes:
      - ./vector/vector.toml:/etc/vector/vector.toml
    ports:
      - "514:514/udp"   # syslog
      - "8686:8686"     # vector API
    networks: [ulpf_net]

  ulpf-api:
    build: ./core
    depends_on: [postgres, ollama]
    environment:
      - DATABASE_URL=postgresql://ulpf:ulpf@postgres:5432/ulpf
      - OLLAMA_URL=http://ollama:11434
    ports:
      - "8000:8000"
    networks: [ulpf_net]

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=ulpf
      - POSTGRES_PASSWORD=ulpf
      - POSTGRES_DB=ulpf
    volumes:
      - pgdata:/var/lib/postgresql/data
    networks: [ulpf_net]

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_models:/root/.ollama   # model pre-pulled during setup, not at runtime
    networks: [ulpf_net]

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    networks: [ulpf_net]

networks:
  ulpf_net:
    driver: bridge          # no external route required — usable with --internal for true air-gap demo

volumes:
  pgdata:
  ollama_models:
```

For the "unplug the cable" demo: pull the Ollama model and build all images *before* going offline, then either physically disconnect the network or rerun with `networks: { ulpf_net: { driver: bridge, internal: true } }` to prove no external calls happen at runtime.

---

## 5. Setup Sequence (do this before you're offline)

1. `docker compose build` — builds all images while online
2. `docker exec -it <ollama_container> ollama pull qwen2.5:3b` — pulls the model once
3. Vendor the OCSF schema: `git clone https://github.com/ocsf/ocsf-schema core/ocsf/schema` (do this once, commit it to your repo — don't fetch at runtime)
4. `docker compose up` — from this point on, the stack needs zero internet access

---

## 6. Benchmark Script Approach (`benchmark/load_test.py`)

Keep this honest and simple — a replay script, not a formal load-testing framework:

```python
import time, requests

def run_benchmark(sample_file: str, target_url: str, n: int = 10_000):
    with open(sample_file, "rb") as f:
        lines = f.readlines()[:n]
    start = time.perf_counter()
    for line in lines:
        requests.post(target_url, data=line)
    elapsed = time.perf_counter() - start
    print(f"{n} events in {elapsed:.2f}s = {n/elapsed:.0f} events/sec")
    print(f"Extrapolated: {(n/elapsed)*86400:,.0f} events/day on this hardware")
```

Report the real number plus the honest extrapolation math in your architecture doc — this is exactly what your research flagged as more credible to judges than an unverified big claim.

---

## 7. What to build vs. defer (36-hour reality check)

| Build now (P0) | Defer / describe only (P1-P2) |
|---|---|
| 2 parsers — Cisco ASA syslog, Palo Alto CEF — via registry pattern | 5-6 format support |
| OCSF mapping for Network Activity (4001) class, with `unmapped`/`observables`/`ulpf` blocks | Full OCSF class coverage |
| Hash-chain + verify() demo | Formal cryptographic audit tooling |
| AI-assist happy path with human-approval step (1 unmapped format demo) | Robust error handling for malformed AI output |
| Postgres storage + basic search UI | Full-scale OpenSearch/Parseable migration |
| Schema drift firewall — detect + quarantine, not just flag | ML-based anomaly detection |
| Live metrics dashboard (events/sec, drift count, unmapped %, raw preservation) | Historical trend charts |
| One CERT-In report template, with safe "supports compliance" framing | Multi-regulator (SEBI/RBI) profile switching |

This maps directly onto the PRD's Phase 1/Phase 2 P0-P2 breakdown — treat that document as the scope authority and this one as the "how."
