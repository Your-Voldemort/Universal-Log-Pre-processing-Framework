<div align="center">

# ULPF — Universal Log Pre-processing Framework

**Lossless, air-gapped normalization of perimeter-device security logs into [OCSF](https://ocsf.io)**

![Python](https://img.shields.io/badge/python-3.12-blue)
![Next.js](https://img.shields.io/badge/next.js-14-black)
![OCSF](https://img.shields.io/badge/schema-OCSF-orange)
![Docker](https://img.shields.io/badge/deploy-docker--compose-2496ED)
![Status](https://img.shields.io/badge/status-MVP-yellow)

Built for **SIH26156** (NTRO / NCIIPC · Blockchain & Cybersecurity)

[Overview](#overview) • [Features](#features) • [Getting started](#getting-started) • [Architecture](#architecture) • [API](#api-reference) • [Development](#development)

</div>

---

## Overview

Security teams pull logs from dozens of heterogeneous perimeter devices — firewalls, IDS/IPS, routers — each in a different format (Syslog, CEF, LEEF, JSON). Every new source needs a hand-built parser before it's usable in a SIEM. ULPF ingests any of these formats and outputs one consistent, lossless, forensically-traceable schema, entirely offline after initial setup.

```
Perimeter device logs → Ingestion (Vector) → Parser registry
   → [known format] → OCSF mapper + hash chain → dual storage (raw + normalized)
   → [unknown format] → local AI-assist → human approval → new parser
Dual storage → Schema Drift Firewall (quarantine) + Search & Compliance API → Dashboard
```

> [!NOTE]
> This repo is a reference implementation, not the full spec. `SIH26156-ULPF-PRD.md` is the master planning document — read it first for the complete picture. `SIH26156-ULPF-Technical-Implementation.md`, `SIH26156-ULPF-MVP-Build-Brief.md`, and the two feasibility/market reports hold the depth behind the decisions below.

## Features

| | |
|---|---|
| **Compliance-native by default** | Built-in CERT-In profile (180-day retention, Indian-jurisdiction, NTP sync). Auto-drafts a CERT-In-format incident report directly from normalized OCSF data. |
| **Air-gapped by architecture** | Zero phone-home, zero license-check callbacks. The OCSF schema and AI model weights are vendored/pulled once during setup — never fetched at runtime. |
| **Provable losslessness** | Every raw log is SHA-256 hash-chained to its normalized OCSF record (Certificate-Transparency-style). `HashChain.verify()` proves nothing was lost or altered — it doesn't just claim it. |
| **Local AI mapping copilot** | An unrecognized format gets a proposed OCSF mapping from a small local model (Ollama, no cloud call). A human must approve it before it becomes an active parser — the model never runs in the live ingestion path. |
| **Schema Drift Firewall** | A known source's fields changing type or shape unexpectedly — a real, documented OCSF failure mode — quarantines the event instead of silently dropping or mis-mapping it. Three reviewer actions: quarantine / auto-fix / ignore. |

> [!IMPORTANT]
> Every CERT-In/SEBI/NCIIPC reference — in the UI, generated reports, and this README — uses one fixed sentence: *"ULPF provides technical controls and evidence that support applicable CERT-In/SEBI/NCIIPC requirements."* Compliance is a property of an organization's whole posture, not something a normalization tool certifies on its own; ULPF never claims otherwise.

## Getting started

### Prerequisites

- Docker and Docker Compose
- ~4 GB free disk for images + the local AI model

### Quick start

```bash
git clone <this-repo>
cd "Universal Log Pre-processing Framework"
docker compose build
```

> [!TIP]
> Pull the local model once, while you're still online — it's never fetched again at runtime:
> ```bash
> docker exec -it $(docker compose ps -q ollama) ollama pull qwen2.5:3b
> ```

```bash
docker compose up
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API (docs at `/docs`) | http://localhost:8000 |
| Syslog / CEF ingestion | UDP/TCP 514 (via Vector), or `POST /ingest` directly |

### Try it

```bash
curl -X POST http://localhost:8000/ingest --data-binary @- <<'EOF'
<166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound TCP connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) to inside:10.10.1.20/52341 (10.10.1.20/52341)
EOF
```

The response is a validated OCSF event with `unmapped`, `observables`, and `ulpf` (traceability) blocks — see [`testdata/sample_logs.txt`](testdata/sample_logs.txt) for the literal sample lines used throughout the build brief.

### Demo data

For a dashboard that isn't empty — 45 events across both vendor formats, a realistic denied port-scan burst (good material for the Compliance Report tab), and 3 unrecognized-format lines for the AI-assist demo:

```bash
python3 testdata/seed_demo_data.py testdata/demo_logs.txt http://localhost:8000/ingest
```

### Air-gap proof

Add `internal: true` under `networks.ulpf_net` in `docker-compose.yml`, or physically disconnect the network — the stack keeps ingesting and querying with zero external calls. Verified: with `internal: true` set, the API container cannot resolve or reach any external host, yet `/ingest`, `/mapping/*`, and `/verify-chain` all keep working.

> [!NOTE]
> On rootless Docker, published host ports can stop responding once `internal: true` is set (container-to-container traffic is unaffected). If `curl localhost:8000/health` goes quiet, verify from a sibling container on `ulpf_net` instead — that's also the more realistic "still serving the internal LAN" demo shape.

### Rootless Docker: two known quirks

Both are host-environment issues, not application bugs — standard/Desktop Docker doesn't hit either one.

1. **Vector's port 514 needs a privileged-port grant.** Rootless Docker refuses to bind ports below 1024 by default (`cannot expose privileged port 514`). Fix once:
   ```bash
   sudo sysctl -w net.ipv4.ip_unprivileged_port_start=514   # add to /etc/sysctl.conf to persist
   ```

2. **A bare `docker compose up`/`up -d` can fail with `address already in use` on port 8000, even when nothing else is using it.** Because `vector` depends on `ulpf-api`, Compose tries to restart the already-running `ulpf-api` container as part of dependency reconciliation on every `up` — and on this daemon, that self-restart can race its own still-held port binding. If `ulpf-api` is actually already healthy (`curl localhost:8000/health`), bring up just the missing service instead of re-running the full `up`:
   ```bash
   docker compose up -d --no-deps vector
   ```

## Architecture

| Layer | Technology |
|---|---|
| Ingestion | [Vector](https://vector.dev) (Rust, single binary, no phone-home) |
| Core engine / API | Python 3.12, FastAPI, Pydantic |
| OCSF validation | `jsonschema` against a locally vendored schema subset — no runtime fetch |
| AI-assist | [Ollama](https://ollama.com) (local), `qwen2.5:3b`, quantized |
| Hash-chain integrity | Python `hashlib` (SHA-256), custom chain module |
| Storage | PostgreSQL 16 + JSONB (raw index + normalized store), connection-pooled |
| Compliance templating | Jinja2 → Markdown |
| Frontend | Next.js 14 (App Router) + React + Tailwind CSS |
| Orchestration | Docker Compose |

<details>
<summary>Repository structure</summary>

```
.
├── docker-compose.yml
├── vector/vector.toml              # raw-byte-preserving ingestion config
├── core/
│   ├── main.py                     # FastAPI entrypoint
│   ├── parsers/                    # BaseParser, vendor parsers, registry
│   ├── ocsf/                       # mapper, YAML mappings, vendored schema
│   ├── storage/                    # hash chain, raw store, normalized store
│   ├── drift/                      # Schema Drift Firewall + quarantine
│   ├── ai_assist/                  # Ollama client, mapping proposals
│   ├── compliance/                 # CERT-In profile + report generator
│   └── api/                        # route handlers
├── frontend/
│   ├── app/                        # Next.js App Router pages
│   ├── components/                 # DashboardMetrics, SearchTable, DriftAlerts, …
│   └── lib/api.ts                  # typed fetch client
├── benchmark/load_test.py          # honest replay-based throughput check
└── testdata/sample_logs.txt        # literal sample lines used throughout
```

</details>

## API reference

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/ingest` | Raw log bytes in → parsed, mapped, stored, or quarantined |
| `GET` | `/search?q=&source=&limit=` | Substring search over normalized events |
| `GET` | `/events/{raw_event_id}` | Raw log + normalized OCSF event, cross-referenced |
| `GET` | `/verify-chain` | Replays the full hash chain — `true` unless tampered |
| `GET` | `/metrics` | Dashboard tile data |
| `GET` | `/drift/quarantine` | List quarantined events |
| `POST` | `/drift/quarantine/{id}/resolve` | `{"action": "quarantine" \| "auto-fix" \| "ignore"}` |
| `POST` | `/drift/inject-malformed` | Demo button — flips a known field's type to trigger drift |
| `POST` | `/mapping/propose` | `{"raw_samples": "..."}` → local-LLM-drafted OCSF mapping |
| `GET` | `/mapping/proposals` | List pending/approved proposals |
| `POST` | `/mapping/{id}/approve` | Human approval — writes the YAML, hot-reloads the parser registry |
| `POST` | `/compliance/report` | `{"raw_event_ids": [...]}` → CERT-In-format Markdown report |
| `GET` | `/compliance/profile` | Active retention/jurisdiction/NTP profile |

## Development

### Backend, without Docker

```bash
uv venv --python 3.12 .venv
uv pip install -p .venv -r core/requirements.txt

docker run -d --name ulpf-postgres-dev -e POSTGRES_USER=ulpf -e POSTGRES_PASSWORD=ulpf \
  -e POSTGRES_DB=ulpf -p 5433:5432 postgres:16-alpine

cd core
DATABASE_URL=postgresql://ulpf:ulpf@localhost:5433/ulpf ../.venv/bin/uvicorn main:app --reload
```

Every component also runs as a standalone self-check:

```bash
cd core
../.venv/bin/python -m storage.hashchain
../.venv/bin/python -m parsers.registry
../.venv/bin/python -m ocsf.mapper
../.venv/bin/python -m drift.firewall
../.venv/bin/python -m ai_assist.ollama_client
../.venv/bin/python -m compliance.report_generator
```

### Frontend, without Docker

```bash
cd frontend
npm install
API_BASE_URL=http://localhost:8000 npm run dev   # :3000, rewrites proxy to :8000
npm run build && npm run start                   # production build + standalone server
```

> [!NOTE]
> The API rewrites in `next.config.js` are resolved into the build manifest at `next build` time, not re-read at container start — the Docker image bakes in `API_BASE_URL=http://ulpf-api:8000` (the compose-network hostname) at build time. Set the env var before `dev`/`build` for any other target.

### Benchmark

```bash
python3 benchmark/load_test.py testdata/sample_logs.txt http://localhost:8000/ingest 1000
```

An honest replay script, not a formal load-testing framework — it reports the real number, not a target.

## Known simplifications

MVP scope, not oversights — see the Build Brief for what's deliberately deferred:

- OCSF schema is a hand-vendored subset covering Network Activity (`class_uid` 4001) only, not the full `ocsf/ocsf-schema` repo. Sufficient for the 2 built-in parsers; extend `core/ocsf/schema/` for more classes.
- Search is `ILIKE` over a JSONB text cast, not a tsvector/GIN query — fine at hackathon data volumes.
- Schema-drift signatures are in-memory per process (reset on restart) — fine for a live demo session.

## Resources

- [`SIH26156-ULPF-PRD.md`](SIH26156-ULPF-PRD.md) — product spec, scope, differentiators, phased plan
- [`SIH26156-ULPF-Technical-Implementation.md`](SIH26156-ULPF-Technical-Implementation.md) — architecture rationale, code skeletons
- [`SIH26156-ULPF-MVP-Build-Brief.md`](SIH26156-ULPF-MVP-Build-Brief.md) — the build spec this implementation follows
- [`SIH26156-ULPF-Feasibility-Market-Report.md`](SIH26156-ULPF-Feasibility-Market-Report.md) · [`ULPF-feasibility-competitive-analysis-market-research.md`](ULPF-feasibility-competitive-analysis-market-research.md) — market/regulatory validation
- [OCSF Schema](https://schema.ocsf.io) · [CERT-In Directions, 2022](https://www.cert-in.org.in) · [NCIIPC](https://nciipc.gov.in)
