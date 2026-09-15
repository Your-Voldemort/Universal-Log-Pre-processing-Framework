# Product

## Register

product

## Users

**Primary: SOC analysts** at Indian enterprises and at government and critical-infrastructure bodies (the NCIIPC-aligned sectors: power, banking, telecom, transport). They work long shifts, often on dim SOC floors across several monitors. They use ULPF to see logs from heterogeneous perimeter devices (Cisco ASA, Palo Alto, Juniper SRX, Check Point, Suricata) as one OCSF-normalized stream, trace any normalized event back to its untouched raw bytes, and clear the schema-drift quarantine queue.

**Secondary:**

- **Compliance and forensics officers**, usually in daylit offices, who draft CERT-In-format incident reports and need to show log integrity under audit.
- **SIEM and platform engineers** who onboard a new log source through an AI-proposed, human-approved mapping instead of a hand-written parser.

Evaluators (the SIH jury, procurement teams) see the same console. It is credible because it is real operational software, not a demo skin.

## Product Purpose

ULPF ingests perimeter security logs in any vendor format and outputs one lossless, forensically traceable OCSF schema, fully offline after setup. The console is where operators watch pipeline health, search and trace events, resolve quarantined drift, approve new parsers, verify the hash chain, and draft incident reports.

Success: an analyst goes from "something looks off" to raw-byte evidence in a few clicks, and trusts every number on screen because each one links to the record behind it.

## Brand Personality

**Precise, calm, accountable.**

The voice is plain, exact, and evidentiary: say what the system did and what it can prove, never what it "ensures". It serves corporate and government buyers equally: institutional enough for a national SOC, crisp enough for an enterprise security team. Confidence comes from density, accuracy, and traceability, not theatrics.

Compliance language is fixed everywhere it appears: *"ULPF provides technical controls and evidence that support applicable CERT-In/SEBI/NCIIPC requirements."*

Reference products, and what to take from each:

- **Microsoft Sentinel / Defender**: institutional familiarity; incident list with a detail pane.
- **Datadog / Elastic**: facets, time-range control, log detail drawer, information density.
- **Linear / Stripe Dashboard**: typographic restraint and complete component states.
- **CrowdStrike Falcon / Palo Alto Cortex**: severity-driven triage.

## Anti-references

- Hollywood "hacker" consoles: neon green or cyan on black, glitch effects, scanlines, spinning globes with attack arcs.
- Skeuomorphic props: the previous brass instrument-panel and wax-seal look, gunmetal textures, grid-paper backgrounds.
- Generic SaaS dashboards: hero-metric tiles with gradient accents, identical card grids, decorative charts with no drill-down.
- Consumer-app softness: oversized radii, pastel gradients, playful illustration.
- Anything that implies certification: "compliant" badges, shield-with-checkmark compliance seals.

## Design Principles

1. **Evidence over assertion.** Every status, count, and verdict links to the record that proves it: raw event, hash, quarantine item, proposal.
2. **Calm until it matters.** Neutral at rest. Color and motion are reserved for state that needs action: drift, tampering, denied traffic, pending approval.
3. **Density with hierarchy.** Analysts on long shifts need many rows and fields in view. Hierarchy comes from type weight, alignment, and spacing, not from boxes around everything.
4. **One vocabulary everywhere.** The same button, table, status, and time format on every screen. Times are always UTC and labeled as such.
5. **Honest language.** Plain verbs, exact numbers, no compliance overclaims, no marketing adjectives.

## Accessibility & Inclusion

- WCAG 2.2 AA and GIGW 3.0 (Guidelines for Indian Government Websites).
- Light and dark themes that follow the system setting, with a manual switch. Both meet AA: 4.5:1 for text, 3:1 for UI components and focus indicators.
- Fully keyboard operable, visible focus, skip link, proper landmarks.
- Status is never conveyed by color alone: always a text label, plus an icon or shape where it helps scanning.
- `prefers-reduced-motion` is respected.
- Tabular numerals for data. Plain English copy, readable for non-native English speakers.
