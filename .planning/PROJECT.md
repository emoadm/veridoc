# VeriDoc AI

AI-powered Source Data Verification (SDV) platform for clinical trials — a fleet of
specialized AI agents that verify EMR source data against Medidata Rave eCRF data
with a full ALCOA+ / 21 CFR Part 11 audit trail.

## Core Value

Traditional on-site SDV consumes 30–35% of total trial costs and is a primary
timeline bottleneck. VeriDoc AI replaces manual field-by-field verification with a
fleet of specialized, continuously-running AI agents that compare EMR source data
against Medidata Rave eCRF entries, assess every source document against the ALCOA+
framework, and emit prioritized, structured discrepancy queries — all under a
tamper-evident audit trail and mandatory human-in-the-loop review.

The platform is a **decision-support tool**, not an autonomous decision-maker. Every
clinical decision is routed to a qualified human for review and approval.

## Milestone Scope (Milestone 1: Buildable Phase-1 Core)

This milestone covers ONLY the engineering work that does **not** depend on external
prerequisites (regulatory sign-off, Medidata production API access, signed pilot
client). It delivers the SDV engine, agent fleet, integrations (against mocks/
fixtures), and portals — verifiable end-to-end against synthetic data.

**First-milestone developer success metric:**
The SDV engine, driven by the orchestrator + specialized agents, ingests synthetic
FHIR R4 EMR data and a Medidata Rave mock, performs field-level + semantic
comparison, and emits structured, prioritized discrepancy queries with ALCOA+
assessment and a complete, tamper-evident audit trail — all verifiable end-to-end
against fixtures.

### In scope (this milestone)
1. Platform/architecture skeleton: monorepo, cloud-native service scaffold, CI/CD,
   audit-trail infrastructure from day one (21 CFR Part 11-ready), RBAC/identity baseline.
2. FHIR R4 Unified Patient Data Model + heterogeneous source ingestion. Source
   modality varies per clinical site — some sites are EMR-based, some paper/scanned
   only, some mixed — so site source profile is configurable and every path (native
   FHIR, HL7 v2.x, proprietary API, semi-manual PDF/Excel, paper/scanned OCR)
   normalizes to the same canonical FHIR R4 model (native EMR adapters exercised
   against synthetic FHIR). See `CON-source-heterogeneity`.
3. Medidata Rave integration against a **mock** of the MDRWS API.
4. Multi-agent framework + Orchestrator Agent (LangGraph), with human-in-the-loop
   gating baked in.
5. Core verification agents: SDV, ALCOA+, Lab, AE/SAE, ConMed, Consistency.
6. Query Agent (query lifecycle against the Rave mock), Risk Agent, Report Agent.
7. CRA + Sponsor portals (React) and the audit-trail review UI.

### Deferred to future milestones (out of scope here)
eTMF integration; additional eCRF integrations (Veeva EDC / Oracle Inform / REDCap);
Japan/Brazil/Middle-East EMR adapters; enterprise / white-label tier; ISO 27001
certification; multi-region cluster rollout; China isolated instance; predictive
analytics; AI model fine-tuning.

### Explicitly out of scope for the product (Phase-1 product boundary)
eCRF replacement (integration only); CTMS functionality; pharmacovigilance database
submission (MedWatch / EudraVigilance); direct patient-facing interfaces;
statistical analysis plan execution; biostatistics / data management functions.

## Target Runtime

Cloud-native web platform.
- **Backend / AI:** Python — LangGraph multi-agent orchestration, Claude / GPT-4 LLM
  engine, OCR engine.
- **Frontend:** React.js + TypeScript over REST / GraphQL.
- **Data:** PostgreSQL + MongoDB + Redis + blob store.
- **Infra:** Kubernetes on AWS or Azure (cloud provider DEFERRED — see open decisions).

## Parallel Constraints (tracked, NOT blocking phases in this milestone)

These are real prerequisites for **commercial deployment**, not for build start. They
run in parallel to engineering and must be tracked, but they do not gate any phase in
this milestone.

- **CON-regulatory-strategy-first** — Regulatory Affairs strategy + CSV plan
  (21 CFR Part 11, EMA Annex 11, ICH E6(R3)). A hard prerequisite before *commercial*
  development; for this internal "buildable core" milestone, the skeleton must be
  built validation-ready, but the strategy itself runs in parallel.
- **CON-medidata-partner** — Official Medidata Technology Partner status. Gates
  **production** Rave API access. This milestone builds against a Rave **mock** and an
  abstraction layer, so it is non-blocking here.
- **CON-iq-oq-pq-validation** / **CON-gamp5-csv** — GAMP 5 CSV lifecycle
  (URS → FS → DQ → IQ → OQ → PQ). IQ/OQ begin late in product Phase 1; **PQ completion
  and production Rave access gate COMMERCIAL deployment, not build start.** Validation-
  ready documentation is produced throughout, but full validation is out of this
  milestone's gating path.
- **CON-pilot-partner** — Pilot CRO/Sponsor partner engaged during design. A business
  prerequisite for real-world validation; non-blocking for the buildable core.

## Decisions

<decision id="DEC-fhir-r4-canonical" status="locked">
All EMR data is normalized to the **FHIR R4 Unified Patient Data Model** before
processing. FHIR R4 is the canonical internal representation; HL7 v2.x, proprietary
APIs, semi-manual imports, and OCR all map into FHIR R4 (DocumentReference, etc.).
Source: PRD section 3.3. Status: embedded-authoritative (PRD-derived), treated as locked.
</decision>

<decision id="DEC-rave-primary-ecrf" status="locked">
**Medidata Rave** (via the MDRWS API) is the primary eCRF integration target. Other
eCRFs (Veeva EDC, Oracle Inform, REDCap) are deferred to a future milestone; platform
positioning remains eCRF-agnostic long-term.
Source: PRD "Proposed Solution", section 3.4. Status: embedded-authoritative, treated as locked.
</decision>

<decision id="DEC-human-in-the-loop" status="locked">
VeriDoc AI operates as a **decision-support tool only**. A mandatory human-in-the-loop
architecture is maintained for ALL clinical decisions (SAE causality, protocol
deviation, clinical significance of labs, complex query closure, site escalation,
regulatory reporting, study halt). Each of the 10 agents carries a defined human-
escalation trigger. This is a binding architectural constraint, not a configurable option.
Source: PRD Critical Success Factors #5, sections 3.2 / 4.4. Status: embedded-authoritative, treated as locked.
</decision>

<decision id="DEC-gamp5-csv" status="locked">
Computer System Validation follows the **GAMP 5** framework lifecycle
(URS → FS → DQ → IQ → OQ → PQ → Ongoing Validation). Validation-ready documentation is
produced throughout development. IQ/OQ/PQ completion is required before *commercial*
deployment (gates commercial release, not this build milestone).
Source: PRD section 4.2. Status: embedded-authoritative, treated as locked.
</decision>

<decision id="DEC-regional-data-residency" status="locked">
**Regional cloud data residency** is required from day one: Americas (AWS us-east),
EMEA (Azure West Europe), APAC (AWS ap-southeast), and an isolated China instance.
GDPR and PIPL compliance by design. Architecture must support regional isolation even
though multi-region rollout itself is deferred.
Source: PRD sections 3.1 / 3.5. Status: embedded-authoritative, treated as locked.
</decision>

<decision id="DEC-cloud-provider" status="open">
**Cloud infrastructure provider (AWS vs Azure) is UNDECIDED.** Deferred to an early
Next Step, to be made "based on initial target market geography." The architecture
references both AWS and Azure components. Infrastructure abstractions (Terraform,
Kubernetes) should remain provider-portable until this decision is made.
Source: PRD section 8, Next Steps #4. Status: open / deferred.
</decision>

## Coding & Interoperability Standards (binding)

Verification correctness depends on standard terminologies (CON-coding-standards):
- **SNOMED CT** and **MedDRA** — semantic clinical terminology matching
- **LOINC** — laboratory result coding
- **CTCAE v5.0 / NCI** — lab and AE grading
- **ATC / WHO Drug Dictionary** — concomitant medication coding

## Security & Compliance Baseline (binding from day one)

- 21 CFR Part 11: electronic signatures, complete time-stamped audit trail, access
  controls, validated-system status.
- EMA Annex 11: change control, data-integrity controls, backup/recovery, audit-trail review.
- GDPR Art. 9: pseudonymization at ingestion, residency enforcement, right-to-erasure.
- HIPAA/HITECH: PHI encryption at rest (AES-256) and in transit (TLS 1.3).
- Audit trail: complete, immutable, 15-year minimum retention.
- Access control: RBAC, MFA, session management, IP allowlisting; HSM key management;
  field-level encryption for PII.
