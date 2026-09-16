<div align="center">

<img src="./frontend/app/icon.svg" alt="" align="center" height="64" />

# ULPF: Universal Log Pre-processing Framework

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![OCSF](https://img.shields.io/badge/Schema-OCSF-ff7000?style=flat-square)](https://schema.ocsf.io)
[![Ollama + Qwen2.5](https://img.shields.io/badge/Ollama-qwen2.5:3b-555?style=flat-square&logo=ollama&logoColor=white)](https://ollama.com/library/qwen2.5)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](docker-compose.yml)
[![Status: MVP](https://img.shields.io/badge/Status-MVP-yellow?style=flat-square)](#scope-and-limitations)

[Overview](#overview) • [Features](#features) • [Getting started](#getting-started) • [Development](#development) • [API](#api-reference) • [Troubleshooting](#troubleshooting) • [Resources](#resources)

</div>

Normalize security logs from any perimeter device (firewalls, IDS/IPS, routers) into one lossless, forensically traceable [OCSF](https://schema.ocsf.io) schema, **fully offline after setup**. Built for **SIH26156** (NTRO / NCIIPC, Blockchain & Cybersecurity).

> [!IMPORTANT]
> ULPF provides technical controls and evidence that support applicable CERT-In/SEBI/NCIIPC requirements. Compliance depends on an organization's whole security posture. A normalization tool can't certify it on its own.

## Overview

A SOC collects logs from many vendors: Syslog from Cisco ASA, CEF from Palo Alto, structured syslog from Juniper SRX, JSON from Suricata. Each format needs its own parser before a SIEM can use it. ULPF accepts all of them over one endpoint and outputs validated OCSF events. Every normalized event links back to its original raw bytes through a SHA-256 hash chain.

```mermaid
flowchart LR
    A["Perimeter devices<br/>Syslog · CEF · JSON"] -->|"UDP/TCP 514 · HTTP 8080"| B[Vector]
    B -->|"POST /ingest (raw bytes)"| C["Raw store<br/>SHA-256 hash chain"]
    C --> D{Parser registry}
    D -->|known format| E[Schema Drift Firewall]
    E -->|signature matches| F["OCSF mapper<br/>+ schema validation"]
    E -->|drifted| G[Quarantine]
    G -->|"auto-fix / ignore"| F
    F --> H[(Normalized store)]
    D -->|unknown format| I["Local LLM proposal<br/>(Ollama)"]
    I -->|human approves| J[New parser + replay]
    J --> D
```

The console is a Next.js app for SOC analysts and compliance officers. It has light and dark themes and is built to WCAG 2.2 AA.

| Page | What it's for |
|---|---|
| **Overview** | Pipeline health: ingest rate, events per source, drift per source, unmapped-field ratio, chain status |
| **Events** | Search normalized events and view each one next to its raw log |
| **Drift quarantine** | Review events whose field types changed, then keep, auto-fix or release them |
| **Parser proposals** | Approve or reject parsers the local AI drafts for unrecognized formats |
| **Integrity** | Re-verify the whole hash chain against the raw bytes on disk |
| **Incident reports** | Draft CERT-In-format incident reports from selected events |

## Features

- **Five built-in parsers**: Cisco ASA syslog, Palo Alto CEF, Juniper SRX `RT_FLOW`, Check Point Log Exporter and Suricata EVE. Output is OCSF Network Activity (`4001`) or Detection Finding (`2004`), validated against a vendored schema.
- **Provably lossless**: raw bytes are preserved exactly (Vector uses raw `socket` sources, not the parsing `syslog` source) and hash-chained. `/verify-chain` re-hashes every raw event from disk, so it catches edited bytes and deleted events, including the most recent ones.
- **Air-gapped by design**: no telemetry and no license callbacks. The OCSF schema is vendored, and the model is pulled once during setup. Nothing is downloaded at runtime.
- **Local AI mapping copilot**: for an unrecognized format, a small local model (`qwen2.5:3b` via Ollama) drafts an OCSF mapping. A person has to approve it. Approval hot-reloads the parser registry and replays earlier unrecognized events. The model never runs in the live ingestion path.
- **Schema Drift Firewall**: when a known source's field changes type or shape, the event is quarantined instead of being dropped or mis-mapped. A reviewer can keep it held, auto-fix it (lossless type coercion only) or ignore the drift. Either release records what was done in `ulpf.drift_resolution`.
- **Compliance built in**: a CERT-In profile (180-day retention, Indian jurisdiction, 6-hour reporting deadline, NPL time sync) and Markdown incident reports generated from the normalized events.

## Getting started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose
- About 4 GB of free disk for the images and the local model

### Run with Docker Compose

```bash
git clone https://github.com/Your-Voldemort/Universal-Log-Pre-processing-Framework.git
cd Universal-Log-Pre-processing-Framework
docker compose up -d --build
```

Pull the AI-assist model once, while you're still online:

```bash
docker compose exec ollama ollama pull qwen2.5:3b
```

> [!TIP]
> The model is only needed for **Parser proposals**. Ingestion, search, drift review, integrity checks and reports all work without it.

| Service | Address |
|---|---|
| Console | http://localhost:3000 |
| API (interactive docs at `/docs`) | http://localhost:8000 |
| Syslog / CEF ingestion (Vector) | UDP/TCP `514` |
| HTTP ingestion (Vector) | `http://localhost:8080` |

### Send your first log

```bash
curl -X POST http://localhost:8000/ingest --data-binary \
  '<166>Aug 30 2026 14:22:31 ASA-FW01 : %ASA-6-302013: Built outbound TCP connection 8847123 for outside:172.16.1.50/443 (172.16.1.50/443) to inside:10.10.1.20/52341 (10.10.1.20/52341)'
```

The response contains the validated OCSF event. Next to the standard fields it includes an `unmapped` bucket (vendor fields with no OCSF equivalent), `observables`, and a `ulpf` block with the `raw_event_id` and the mapping confidence.

### Load demo data

To fill the console, seed 64 events from all five formats. The set includes a denied port-scan burst, which works well for an incident report, and 3 unrecognized lines for the AI-assist flow:

```bash
python3 testdata/seed_demo_data.py testdata/demo_logs.txt http://localhost:8000/ingest
```

### Air-gapped mode

Add `internal: true` under `networks.ulpf_net` in [`docker-compose.yml`](docker-compose.yml), or disconnect the machine from the network. The stack keeps ingesting, mapping and verifying, and it can't reach any external host.

## Development

### Backend

```bash
uv venv --python 3.12 .venv
uv pip install -p .venv -r core/requirements.txt

docker run -d --name ulpf-postgres-dev -e POSTGRES_USER=ulpf -e POSTGRES_PASSWORD=ulpf \
  -e POSTGRES_DB=ulpf -p 5433:5432 postgres:16-alpine

cd core
DATABASE_URL=postgresql://ulpf:ulpf@localhost:5433/ulpf ../.venv/bin/uvicorn main:app --reload
```

See [`.env.example`](.env.example) for the other variables (`OLLAMA_URL`, `OLLAMA_MODEL`, `ULPF_RAW_DIR`).

### Frontend

```bash
cd frontend
npm install
API_BASE_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

The console calls the API through the `/api/*` rewrite in [`next.config.js`](frontend/next.config.js).

> [!NOTE]
> `next build` resolves rewrites into the build output, so `API_BASE_URL` has to be set **at build time**. The Docker image bakes in `http://ulpf-api:8000`, the Compose network hostname.

### Tests

Most modules include a self-check that runs without a database:

```bash
cd core
for m in storage.hashchain storage.raw_store parsers.registry parsers.cisco_asa_syslog \
         parsers.paloalto_cef parsers.juniper_srx parsers.checkpoint parsers.suricata_eve \
         parsers.generic_kv ocsf.mapper drift.firewall ai_assist.ollama_client \
         compliance.report_generator api.routes_search; do
  ../.venv/bin/python -m "$m" || break
done
```

[`core/tests/test_e2e.py`](core/tests/test_e2e.py) runs the real API against Postgres. It covers every built-in format, drift quarantine and release, the AI-assist approval guards and replay, hash-chain tamper detection, time-range search and the compliance report. It doesn't need Ollama.

> [!WARNING]
> The end-to-end tests **TRUNCATE every ULPF table** in `ULPF_TEST_DATABASE_URL`. Point them at a throwaway database. The example below uses port 5434 so it can't hit the 5433 dev database.

```bash
docker run -d --rm --name ulpf-test-pg -e POSTGRES_USER=ulpf -e POSTGRES_PASSWORD=ulpf \
  -e POSTGRES_DB=ulpf -p 5434:5432 postgres:16-alpine

cd core
ULPF_TEST_DATABASE_URL=postgresql://ulpf:ulpf@localhost:5434/ulpf ../.venv/bin/python tests/test_e2e.py
docker stop ulpf-test-pg
```

### Benchmark

```bash
python3 benchmark/load_test.py testdata/sample_logs.txt http://localhost:8000/ingest 1000
```

Last measured result (2026-09-15): **196 events/sec**, or 2,000 events in 10.19 s, with `/verify-chain` over those events taking 0.01 s. The client was sequential (one request per event) against a single uvicorn worker on a 12th Gen Core i5 laptop. That measures one-at-a-time throughput, not peak parallel throughput.

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest` | Raw log bytes in. Returns the OCSF event, `quarantined` or `unknown_format` |
| `POST` | `/ingest/replay` | Re-route stored unrecognized events through the current parsers |
| `GET` | `/search?q=&source=&time_range=&limit=` | Search normalized events. `time_range` is an ISO 8601 interval, e.g. `2026-08-30T14:00Z/2026-08-30T15:00Z` (either side may be empty, no zone = UTC) |
| `GET` | `/events/{raw_event_id}` | Normalized OCSF event and its raw log |
| `GET` | `/verify-chain` | `{"verified": true}` unless the chain or raw bytes were tampered with |
| `GET` | `/metrics` | Console overview data |
| `GET` | `/drift/quarantine` | List quarantined events |
| `POST` | `/drift/quarantine/{id}/resolve` | `{"action": "quarantine" \| "auto-fix" \| "ignore"}` |
| `POST` | `/drift/inject-malformed` | Demo: ingest a Cisco ASA event with a drifted field type |
| `POST` | `/mapping/propose` | `{"raw_samples": "..."}` returns a locally drafted OCSF mapping |
| `GET` | `/mapping/proposals` | List proposals |
| `POST` | `/mapping/{id}/approve` | Activate the parser, persist its YAML, replay unrecognized events |
| `POST` | `/mapping/{id}/reject` | Reject a pending proposal |
| `POST` | `/compliance/report` | `{"raw_event_ids": [...]}` returns a CERT-In-format Markdown report |
| `GET` | `/compliance/profile` | Active retention, jurisdiction and time-sync profile |
| `GET` | `/health` | Liveness check |

<details>
<summary><strong>Tech stack and project structure</strong></summary>

| Layer | Technology |
|---|---|
| Ingestion | [Vector](https://vector.dev) |
| API and core engine | Python 3.12, FastAPI, Pydantic |
| OCSF validation | `jsonschema` against a vendored schema subset |
| AI-assist | [Ollama](https://ollama.com) running `qwen2.5:3b` |
| Integrity | SHA-256 hash chain (`hashlib`) |
| Storage | PostgreSQL 16 + JSONB, raw bytes on disk |
| Reports | Jinja2 to Markdown |
| Console | Next.js 14 (App Router), React, Tailwind CSS |

```
├── docker-compose.yml
├── vector/vector.toml         # byte-preserving ingestion
├── core/
│   ├── main.py                # FastAPI entrypoint
│   ├── api/                   # route handlers
│   ├── parsers/               # vendor parsers + registry
│   ├── ocsf/                  # mapper, YAML mappings, vendored schema
│   ├── storage/               # hash chain, raw store, normalized store
│   ├── drift/                 # Schema Drift Firewall + quarantine
│   ├── ai_assist/             # Ollama client, proposal store
│   ├── compliance/            # CERT-In profile + report generator
│   └── tests/test_e2e.py
├── frontend/                  # Next.js console
├── benchmark/load_test.py
└── testdata/                  # sample and demo logs, seed script
```

</details>

## Scope and limitations

This is an MVP. The following limits are intentional (the [Build Brief](SIH26156-ULPF-MVP-Build-Brief.md) covers what's deferred):

- The OCSF schema is a vendored subset covering classes `4001` and `2004`. Adding a class means adding one `*_<class_uid>.schema.json` file to `core/ocsf/schema/`.
- Parser coverage is narrow:
  - **Cisco ASA**: connection build/teardown (302013–302016) and denies (106001, 106006, 106015, 106023, 106100), IPv4 only.
  - **Juniper SRX**: RFC 5424 structured `RT_FLOW_SESSION_*` only.
  - **Check Point**: syslog-format firewall connection logs only.
  - **Suricata**: EVE `alert` events only.

  Anything else keeps its raw bytes and goes to `unknown_format`. FortiGate has no parser on purpose, since it's the AI-assist demo format.
- Device timestamps carry no timezone, so ULPF treats them as UTC. Keep devices on UTC through NTP.
- Search is `ILIKE` over JSONB text, not a full-text index.
- Drift signatures are held in memory and reset when the API restarts.
- The API is built for a single uvicorn worker, because approval and replay use process-wide locks.

## Troubleshooting

<details>
<summary><strong><code>/mapping/propose</code> returns 503 "Ollama model not found"</strong></summary>

The model hasn't been pulled yet. Run `docker compose exec ollama ollama pull qwen2.5:3b` while you're online.

</details>

<details>
<summary><strong>Rootless Docker: <code>cannot expose privileged port 514</code></strong></summary>

Rootless Docker can't bind ports below 1024 by default. Allow it once:

```bash
sudo sysctl -w net.ipv4.ip_unprivileged_port_start=514   # add to /etc/sysctl.conf to persist
```

</details>

<details>
<summary><strong>Rootless Docker: <code>address already in use</code> on port 8000</strong></summary>

`vector` depends on `ulpf-api`, so running `docker compose up` again can restart the API container while the old container still holds its port. If `curl localhost:8000/health` already responds, start only the missing service:

```bash
docker compose up -d --no-deps vector
```

</details>

<details>
<summary><strong>Rootless Docker: host ports stop responding in air-gapped mode</strong></summary>

With `internal: true`, rootless Docker can stop forwarding published host ports. Traffic between containers still works. Verify from a container on `ulpf_net` instead, which is also closer to how an internal-LAN deployment runs.

</details>

## Resources

- [`SIH26156-ULPF-PRD.md`](SIH26156-ULPF-PRD.md): product spec, scope and phased plan (start here)
- [`SIH26156-ULPF-Technical-Implementation.md`](SIH26156-ULPF-Technical-Implementation.md): architecture rationale
- [`SIH26156-ULPF-MVP-Build-Brief.md`](SIH26156-ULPF-MVP-Build-Brief.md): the build spec this implementation follows
- [`SIH26156-ULPF-Feasibility-Market-Report.md`](SIH26156-ULPF-Feasibility-Market-Report.md) and [`ULPF-feasibility-competitive-analysis-market-research.md`](ULPF-feasibility-competitive-analysis-market-research.md): market and regulatory validation
- [`PRODUCT.md`](PRODUCT.md) and [`DESIGN.md`](DESIGN.md): users, product principles and the console design system
- [OCSF Schema](https://schema.ocsf.io) · [CERT-In](https://www.cert-in.org.in) · [NCIIPC](https://nciipc.gov.in)
