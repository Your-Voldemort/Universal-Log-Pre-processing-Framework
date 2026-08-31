# PRD: Universal Log Pre-processing Framework (ULPF)

**Problem Statement SIH26156 | NTRO / NCIIPC | Theme: Blockchain & Cybersecurity | Category: Software**
**Status: strategy validated, differentiators locked, architecture finalized, MVP build brief ready — as of 31 Aug 2026, pre-internal-round**

---

## 0. Document map

This is the master planning document — read it first for the full picture. Three companion documents hold depth this one only summarizes:

- **Feasibility & Market Report** — full market sizing, regulatory deep-dive, competitor-by-competitor feature matrix, SWOT, sources
- **Technical Implementation** — full code skeletons, reasoning behind each stack choice, docker-compose, setup sequence
- **MVP Build Brief** — self-contained spec formatted for an AI coding agent to build the MVP directly from, with sample test data and a milestone-by-milestone build order

---

## 1. Key Dates & Constraints
*(confirm exact dates with your SPOC/Innovation Council — colleges set their own internal deadlines within the national window)*

- PS released: 25 Aug 2026
- Internal hackathon (college-level): early September 2026 — a narrow window from today
- SPOC uploads shortlisted teams to national portal: September 2026
- National review of shortlisted teams: September–October 2026
- Grand Finale (36-hour build): December 2026
- Team rules (per standard SIH format): 6 members including 1 team leader, at least 1 female member mandatory, faculty mentor mandatory, unique team name per problem statement
- SIH's own process assigns finalist teams a mentor between selection and the finale specifically to help build a functional prototype *before* the 36-hour event — the finale is a final integrate/harden/demo sprint, not a from-zero build (see §10.3)

---

## 2. Problem Statement

Security teams monitoring enterprise/government networks pull logs from dozens of heterogeneous perimeter devices — firewalls, IDS/IPS, routers — each in a different format (Syslog, CEF, LEEF, JSON, XML). Every new source needs a hand-built parser before it's usable in a SIEM, which is slow, error-prone, and doesn't scale. NTRO (via NCIIPC, India's critical infrastructure protection body) wants a single framework that ingests any of these formats and outputs one consistent, lossless, forensically-traceable schema.

**"Current Scope" in the official PS is narrower than the background text suggests: perimeter network device logs specifically**, not all logging everywhere. The whole strategy below is anchored to that narrower, achievable scope.

---

## 3. Why This Problem Statement

Selected deliberately, not by default. Reasoning from the original theme/PS survey of all 226 SIH26 problem statements:

- **NTRO/cybersecurity branding filters out casual teams.** "Intelligence agency" framing reads as intimidating, which suppresses the generalist-team competition that floods themes like Smart Automation or generic HealthTech.
- **The actual work is standard backend/data engineering**, not novel research — no ML training pipeline, no niche domain science (unlike, say, Ayurveda-compliance or mining-geology PS also considered).
- **It plays directly to the team's existing strengths**: full-stack, AI tooling, infrastructure — not a domain the team would need to fake expertise in.
- **The PS is unusually well-specified** (named datasets aren't relevant here, but the "Expected Solutions" checklist a–k and explicit deliverable list are concrete enough to build a real rubric against, unlike vaguer PS on the list).

---

## 4. Market & Regulatory Validation (condensed — see Feasibility Report for full detail and sources)

- **CERT-In's 2022 Directions** legally require virtually every regulated Indian entity to retain ICT logs for a rolling 180 days within Indian jurisdiction and report incidents within 6 hours — this is real, binding demand, not hypothetical.
- **NCIIPC/NTRO's mandate** explicitly includes funding indigenous security-tool R&D to reduce foreign-technology dependence in critical infrastructure — this PS is aligned with a live national policy direction, not just a hackathon exercise.
- **Gartner (primary source):** India information-security spending projected at $3.4B in 2026 (+11.7%), with security software the largest, fastest-growing segment, explicitly naming SIEM as a driver.
- **OCSF is a credible, non-invented target schema** — backed by AWS, Cisco, IBM, Splunk, joined the Linux Foundation in Nov 2024, actively maintained (~v1.9, March 2026).
- **The competitive whitespace is real, not fabricated for pitch purposes:** no existing tool combines native OCSF support + genuine air-gapped deployment + a permissive open-source license. Cribl/Splunk Edge Processor/Datadog have OCSF but are commercial/cloud-leaning; NXLog/Vector are air-gap-capable but not OCSF-native; Microsoft Sentinel has neither.
- **Parseable** (Bengaluru, open-source, VC-backed, global cybersecurity/fintech customers) proves an Indian team can build credible log infrastructure that competes internationally — this category is not untested ground for a domestic team.

---

## 5. Goals

**Phase 1 — Internal Round**
- Prove the core normalization concept end-to-end for 2 real vendor log formats
- Demonstrate at least one of the four differentiators (§8) live, not just described
- Convince the college jury the idea is feasible in a 36-hour Grand Finale and meaningfully differentiated

**Phase 2 — Grand Finale**
- Fully satisfy the "Current Scope" — perimeter network device logs, lossless, standardized, analytics-ready
- Hit every item in the PS's "Expected Solutions" checklist (a–k)
- Deliver all 5 official NTRO deliverables in the exact required format
- Demo all four differentiators live, including the two "unfakeable" proof moments (§8)

---

## 6. Non-Goals
*(scope traps specific to this PS — read before building)*

- **Not** proving billion-events/day throughput live. Architect for that scale; demonstrate correctness on a realistic sample with honest, shown-math extrapolation.
- **Not** building parsers for every log format that exists. 2 vendor formats for the MVP (Cisco ASA syslog, Palo Alto CEF), 5–6 for the full Grand Finale build — never "universal" in the literal sense.
- **Not** building a full downstream SIEM/analytics/visualization suite. ULPF's job ends at producing clean, normalized, queryable, quarantine-aware output.
- **Not** pursuing actual air-gapped security certification — demonstrate the capability (zero phone-home, works with the cable pulled), not a certified deployment.
- **Not** training a custom ML anomaly-detection model. The Schema Drift Firewall is a type/field-signature check, not machine learning.
- **Not** claiming regulatory compliance. Every compliance-related claim uses the exact safe framing in §8.1 — never "makes you compliant."

---

## 7. Target Users & User Stories

| Persona | Story |
|---|---|
| SOC Analyst | Wants every log source in one consistent format to correlate events across tools without learning each vendor's schema. |
| Compliance/Forensics Officer | Wants the original raw log preserved and traceable to its normalized version so incident reports hold up under audit. |
| SIEM/Platform Engineer | Wants to onboard a new log source by dropping in one config file, not modifying the core pipeline. |
| Data/ML Engineer (future) | Wants a consistent schema across sources to train detection models without per-source feature engineering. |

---

## 8. The Four Differentiators — What Makes This a Winner, Not Just a Submission

Every competitor on the market either has OCSF or has air-gap — none genuinely has both plus a permissive open-source license (see §4). That gap alone isn't enough to win a hackathon, because every team pitching this PS will land on roughly the same gap. These four pillars are how the gap gets filled in a way that's hard to copy and hard to fake on stage.

### 8.1 Compliance-native by default
Ship built-in regulatory profiles (CERT-In first) so 180-day retention, Indian-jurisdiction enforcement, and NTP sync are on by default, not something a user configures and can misconfigure. Auto-draft the CERT-In-format incident report directly from normalized OCSF data when an event is flagged.
**Safe framing — never deviate from this exact language, anywhere (UI, reports, slides):**
> "ULPF provides technical controls and evidence that support applicable CERT-In/SEBI/NCIIPC requirements."
**Demo moment:** trigger a mock incident live, watch the CERT-In-format report auto-generate in seconds.

### 8.2 Air-gapped by architecture, not by aftermarket
Zero phone-home, zero license-check callbacks, no external dependency at runtime — genuinely offline-first, not cloud-with-an-on-prem-option like every commercial competitor.
**Demo moment (the unfakeable one):** disconnect the network cable mid-demo — or run Docker Compose with `internal: true` networking — and keep ingesting and querying. Most teams claiming "air-gapped support" cannot actually perform this live.

### 8.3 Provable losslessness, not claimed losslessness
Hash-chain every raw log to its normalized OCSF record (SHA-256, Certificate-Transparency-style chaining) so nothing lost or altered is mathematically provable, not just asserted. The output JSON itself carries the proof: an `unmapped` bucket for anything not confidently mapped, `observables` for extracted entities, and a `ulpf` extension block (`raw_event_id`, `raw_event_hash`, `parser_version`, `mapping_confidence`) linking every normalized event back to its untouched original.
**Demo moment:** run `HashChain.verify()` live against the full chain — show it return `True`, then manually edit one stored record and show it correctly return `False`.

### 8.4 Local AI mapping copilot — AI proposes, a human approves, production stays deterministic
When an unrecognized log format arrives, a small locally-run model (Ollama, no cloud call) proposes an OCSF field mapping from a few sample lines. A human must approve it before it becomes an active parser — the model never runs in the live ingestion path for known formats. State this as an explicit architectural rule in the pitch, not an implementation detail: it preempts the obvious judge question ("you're running an LLM in a security pipeline?") before it's asked.
**Demo moment:** hand the judges a log format the team hasn't pre-mapped, onboard it live in under two minutes on stage.

### Supporting 5th feature — Schema Drift Firewall
Not a passive detector: when a known source's field types or structure change unexpectedly (a real, documented OCSF failure mode), the affected event is quarantined — never silently dropped, never silently mis-mapped — with three reviewer actions (quarantine / auto-fix / ignore) surfaced in the UI.
**Demo moment:** an "inject malformed log" button that flips a source's dashboard status to drifted and lands the event in the quarantine queue in real time — the single moment worth rehearsing most.

---

## 9. Technical Architecture (summary — full code in the Technical Implementation doc)

```
Perimeter device logs → Ingestion (Vector) → Parser registry
   → [known format] → OCSF mapper + hash chain → dual storage (raw + normalized)
   → [unknown format] → AI-assist (local LLM) → human approval → new parser
Dual storage → Schema Drift Firewall (quarantine) + Search & Compliance API → Dashboard
```

| Layer | Technology |
|---|---|
| Ingestion | Vector (Rust, single binary, no phone-home) |
| Core engine / API | Python 3.12 + FastAPI + Pydantic |
| OCSF validation | `jsonschema` against a vendored OCSF schema (no runtime fetch) |
| AI-assist | Ollama (local), Qwen2.5-3B or Llama-3.2-3B, quantized |
| Hash-chain integrity | Python `hashlib` (SHA-256), custom chain module |
| Storage | PostgreSQL 16 + JSONB (raw index + normalized store) |
| Compliance templating | Jinja2 → Markdown |
| Frontend | React + Vite + TailwindCSS |
| Orchestration | Docker Compose |

---

## 10. Phase 1 — Internal Round Spec

### Requirements

**P0**
- Parser registry architecture, working end-to-end for 2 formats (Cisco ASA syslog, Palo Alto CEF)
- At least one differentiator demoed live, not just described — recommended: §8.3 (hash-chain verify) or §8.2 (air-gap), both are fast to stage convincingly
- Architecture diagram matching §9

**P1**
- A second differentiator demoed live
- Traceability demo: click a normalized event, see its original raw log via the `ulpf` block

**P2 — mention as roadmap only**
- SIEM/data-lake export connectors, full 5–6 format support, air-gapped installer certification

### 10.1 Pitch deck mapping (standard ~10-slide SIH internal-round format — confirm exact template with your SPOC)

| # | Slide | Content |
|---|---|---|
| 1 | Title | Team, PS ID (26156), college, mentor |
| 2 | Problem Understanding | §2–3 — restate in your own words, cite the "Current Scope" narrowing |
| 3 | Proposed Solution | ULPF one-liner + §9 diagram |
| 4 | Technical Architecture | §9 table + pipeline diagram |
| 5 | Innovation & Novelty | §8 — lead with whichever 2 differentiators you can demo live |
| 6 | Feasibility & Viability | §4 market/regulatory validation, honestly scoped to 2 working formats |
| 7 | Impact & Benefits | Faster SOC onboarding, audit-ready traceability, sovereign/no foreign dependency |
| 8 | Prototype/Demo | Screenshots of the OCSF JSON output (§8.3 example) and dashboard (§8, supporting feature) |
| 9 | 36-Hour Grand Finale Plan | §10.3 below |
| 10 | Team & References | Skills per member, OCSF/NCIIPC/CERT-In references |

### 10.2 Compliance & legal language check
Every slide, report, and UI label referencing CERT-In/SEBI/NCIIPC must use the exact §8.1 framing. This is a one-time check worth doing right before submission — it's the easiest-to-miss detail with the highest downside if a judge catches it.

### 10.3 36-hour reality check (realistic, prep-aware)
SIH's mentorship period means the finale is a final integrate/harden/demo sprint, not a from-zero build. Realistic live-hour budget for a 6-person team:

| Component | Live-hours |
|---|---|
| Ingest + 2 parsers (with prep behind you) | 5–7 |
| Dual storage + hash chain | 3–4 |
| Search UI | 4–5 |
| Docker | 2 |
| Schema drift firewall (lightweight) | 2–3 |
| Throughput test (script, not formal suite) | 1–1.5 |
| Docs, demo video, slides | 4–5 |
| Integration/debugging buffer | 6–8 |

Suggested 6-person split: 2 on ingest+mapping, 1 on storage, 1 on search UI, 1 on Docker/integration (often understaffed — don't skip this role), 1 on benchmark+docs+deck (start by hour 20, not hour 34).

---

## 11. Phase 2 — Grand Finale Spec

### Requirements

**P0**
- All 5–6 parsers at production quality
- Full OCSF-compliant schema with `unmapped`/`observables`/`ulpf` blocks
- Hash-chain + verify() working
- Dockerized, air-gap-verified (network disconnected or `internal: true`)
- Schema Drift Firewall with working quarantine queue and 3 reviewer actions
- AI-assist with human-approval gate
- Architecture Document (max 2 pages), Demo Video (max 2 minutes), Technical Presentation (max 5 slides), Source code + README — exactly as officially specified

**P1**
- SIEM/data-lake export connector (Elasticsearch bulk API or Splunk HEC-compatible JSON)
- Honest throughput benchmark with shown extrapolation math

**P2 — architecture doc only, don't build**
- Plugin marketplace/SDK, true air-gapped certification, multi-tenant support

### Official deliverables checklist
- [ ] Source Code Link (GitHub/Drive)
- [ ] README with setup instructions
- [ ] Architecture Document (max 2 pages)
- [ ] Demo Video (max 2 minutes)
- [ ] Technical Presentation (max 5 slides)

---

## 12. Success Metrics

| Phase | Metric | Target |
|---|---|---|
| Internal Round | Formats demoed end-to-end | 2, both working live |
| Internal Round | Differentiators demoed live (not just slides) | ≥ 1, ideally 2 |
| Grand Finale | Formats fully supported | 5–6, matching "Current Scope" |
| Grand Finale | Traceability | 100% of normalized events link to raw original via `ulpf` block |
| Grand Finale | Air-gap proof | Full pipeline runs with network disconnected, zero errors |
| Grand Finale | Deliverable compliance | All 5 official items submitted in required format/length |

---

## 13. Open Questions

| Question | Who resolves it | Status |
|---|---|---|
| Is the 6-person team + mentor finalized, including ≥1 female member (mandatory)? | Team / SPOC | Open |
| Exact internal hackathon date at your specific college | Innovation Council / SPOC | Open |
| Which 2 differentiators to demo live in the internal round (can't realistically stage all 4 in a short pitch slot) | Team | Open |
| Postgres vs OpenSearch/Parseable for the storage layer — depends on team's existing familiarity | Team (technical call) | Open — Postgres recommended by default, see Technical Implementation §1 |
| Clarify "perimeter network device" scope boundary (e.g., does it include endpoint/IoT logs?) | NTRO helpdesk — helpdesk1@nciipc.gov.in | Open |

---

## 14. Decision Log — how we got here

- **PS selection:** surveyed all 226 SIH26 problem statements across 18 themes; selected SIH26156 for the combination of low expected competition (intimidating NTRO/cybersecurity branding) and strong fit to the team's actual skills (software/AI, not a domain the team would need to fake).
- **Feasibility research:** validated the premise with primary sources — CERT-In's binding 180-day retention mandate, NCIIPC's indigenous-tooling mandate, Gartner's $3.4B India infosec figure, and confirmed a real competitive whitespace (no tool combines OCSF + air-gap + permissive open-source).
- **36-hour reality check:** confirmed via SIH's actual process that the finale sits at the end of a mentored prep period, not a zero-start sprint — this materially changed what scope was judged realistic.
- **Differentiator strategy:** developed the four-pillar positioning (§8) specifically because "we fill the OCSF+air-gap gap" alone isn't defensible — every competing team lands on the same gap.
- **External review adopted:** incorporated six concrete upgrades from an independent review — the safe compliance-language framing, the concrete OCSF JSON example with `unmapped`/`ulpf` blocks, the explicit "AI proposes, human approves" principle, the Schema Drift Firewall's quarantine behavior (not just flagging), real vendor names in the demo narrative, and the specific dashboard metrics spec.
- **External review rejected:** declined a custom Rust rewrite (Python is the correct tool for a 36-hour build given the team's skills), Kafka/Kubernetes/Helm (pure overhead for a single-node judge-facing demo), specific rupee pricing tiers (undefendable if a judge asks), the 14-slide deck structure (conflicts with the sourced ~10-slide SIH template), and 100K+ EPS benchmark targets (higher than what mature production tools actually achieve — report real measured numbers instead).
- **Technical implementation finalized:** locked the stack, wrote full component code skeletons, docker-compose, and setup sequence.
- **MVP build brief created:** repackaged the finalized architecture as a self-contained, LLM-executable spec with real sample log lines and milestone-by-milestone acceptance criteria, for direct use with a coding agent.
