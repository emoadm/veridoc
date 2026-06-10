# VeriDoc AI — Requirements (Milestone 1: Buildable Phase-1 Core)

Requirements for the first milestone. All EMR/eCRF integration is exercised against
synthetic FHIR R4 data and a Medidata Rave **mock** (MDRWS) — no external prerequisite
(regulatory sign-off, production Medidata API, signed pilot) is required to build or
verify any requirement below.

Source: `/home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md` (via `.planning/intel/`).

---

## Platform & Foundation

### PLAT-01 — Platform & architecture skeleton
Monorepo + cloud-native microservice scaffold, provider-portable IaC (Terraform /
Kubernetes), and CI/CD pipeline. Architecture supports regional isolation
(DEC-regional-data-residency) without rolling out multiple regions in this milestone.
- Monorepo with backend (Python) and frontend (React/TS) workspaces
- Service scaffold runs locally and in a single Kubernetes cluster
- CI/CD: lint, test, build, deploy-to-cluster pipeline green
- Cloud-provider abstraction kept portable (DEC-cloud-provider open)

### PLAT-02 — Tamper-evident audit-trail infrastructure (21 CFR Part 11-ready)
*(implements REQ-audit-trail, CON-audit-trail)*
Audit-trail service available from day one; all other services write to it.
- User identity, role, and timestamp captured for every system interaction
- Data accessed/modified/deleted captured with before/after values
- AI agent decisions captured with supporting evidence and confidence scores
- Query lifecycle (generated/modified/closed) captured with rationale
- Configuration changes and all login attempts (success + failure) captured
- Records are append-only / immutable and tamper-evident (hash-chained or equivalent)
- Retention model supports 15-year minimum

### PLAT-03 — RBAC / identity baseline
*(partial of REQ-multi-tenancy-scale; portal surfaces completed in PORTAL-01)*
- 8 user roles defined with distinct access levels (CRA, Data Manager, Medical
  Monitor, Site Coordinator, PI, Sponsor Rep, Regulatory Affairs, System Admin)
- MFA, session management, IP allowlisting hooks
- Multi-site / multi-study tenancy model in the data layer
- Field-level encryption for PII; AES-256 at rest, TLS 1.3 in transit
  *(PII field-level encryption + deterministic pseudonymization + crypto-shred erasure
  delivered in plan 01-03: AES-256-GCM envelope encryption via Google Tink behind a
  portable KMS abstraction, per-patient HKDF key hierarchy. TLS 1.3 in transit is an
  ingress/deploy concern landing with the reference service / Helm charts, 01-05/01-06.)*

---

## Data Ingestion & Integration

### EMR-01 — FHIR R4 Unified Patient Data Model + heterogeneous source ingestion
*(implements REQ-emr-integration, CON-fhir-normalization, DEC-fhir-r4-canonical, CON-source-heterogeneity)*
- FHIR R4 canonical model (Patient, Encounter, Observation, Condition,
  MedicationRequest, AdverseEvent, DiagnosticReport, DocumentReference, Procedure)
- **Per-site source modality is a first-class, configurable property.** Different
  clinical centers use different source documents — some are EMR-based, some are
  paper/scanned only, some are mixed. A site's source profile (EMR / paper / mixed,
  and which ingestion path applies) is configured per site and drives routing.
- Ingestion paths, all normalizing to the SAME canonical FHIR R4 model so everything
  downstream is source-modality-agnostic:
  - Native FHIR R4 adapter (Epic/Cerner/Oracle/NHS) — exercised against **synthetic** FHIR
  - HL7 v2.x adapter mapped to FHIR via translation layer
  - Proprietary-API adapter with FHIR normalization
  - Semi-manual import (structured PDF/Excel with AI extraction) to FHIR
  - **Paper / scanned source documents** via OCR + NLP extraction to FHIR
    DocumentReference (the path for paper-only sites)
- Every ingested unit records its provenance (source modality + ingestion path) so
  downstream agents can adapt — paper-derived data carries OCR confidence and triggers
  ALCOA+ legibility scoring (ALCOA-01); illegible/low-confidence fields are flagged.
- Pseudonymization of patient-identifiable data at ingestion (GDPR Art. 9)

### RAVE-01 — Medidata Rave integration against MDRWS mock
*(implements REQ-rave-integration, CON-rave-primary-ecrf, DEC-rave-primary-ecrf)*
Built against a **mock** MDRWS API behind an abstraction layer (CON-medidata-partner
is parallel/non-blocking; production access is deferred).
- READ: subject data, CRF field values with audit trail, query status, protocol
  deviations, randomization, freeze/lock status
- WRITE: open discrepancy notes (queries), update query status, set per-field SDV
  flags, flag protocol deviations
- WEBHOOKS: triggers on new data entry, SAE submission, query response
- Abstraction layer isolates MDRWS contract so the mock can be swapped for production

---

## Multi-Agent Framework

### AGENT-00 — Multi-agent framework + Orchestrator Agent
*(implements REQ-multi-agent-orchestration, CON-human-in-the-loop, DEC-human-in-the-loop)*
- LangGraph multi-agent framework with stateful agents (defined tools, decision
  logic, escalation pathway each)
- Orchestrator Agent: task planning, agent coordination, priority management;
  escalates conflicting cross-agent findings
- Parallel / continuous monitoring model (not periodic batch)
- Human-in-the-loop gating baked into the framework: every clinical decision routes
  to a qualified human; per-agent escalation triggers enforced
- LLM engine integration (Claude / GPT-4) with confidence thresholds + structured outputs

---

## Core Verification Agents

### SDV-01 — SDV Agent (field-level + semantic comparison)
*(implements REQ-sdv-engine, CON-coding-standards)*
- Exact value matching for numerical data (lab values, vital signs, dates)
- Semantic matching via SNOMED CT / MedDRA mapping layer
- Unit conversion/normalization (mg/dL ↔ mmol/L, °F ↔ °C); date-format normalization
- Multi-language text comparison; missing/partial/illegible data flagging

### ALCOA-01 — ALCOA+ Agent
*(implements REQ-alcoa-compliance)*
- Assess every ingested source document against all 9 ALCOA+ principles
- Attributable / Legible (OCR confidence, flag <95%; escalate <85%) / Contemporaneous /
  Original / Accurate / Complete / Consistent / Enduring / Available
- Defined verification method and query/flag output per principle

### LAB-01 — Lab Agent
*(implements REQ-lab-data-management, CON-coding-standards)*
- LOINC-coded extraction/normalization; verify values/units/dates/methods vs eCRF
- Reference-range comparison; CTCAE v5.0 grading; 3-tier clinical-significance alert
- Trend analysis across visits; protocol-specific threshold monitoring
- Auto cross-reference of significant findings vs AE/SAE

### AESAE-01 — AE/SAE Agent
*(implements REQ-ae-sae-verification)*
- Completeness (all source AEs in eCRF); CTCAE grade verification vs narrative
- Date/outcome consistency; causality-assessment verification
- SAE timeline monitoring (7-day fatal/life-threatening, 15-day other; FDA + EMA)
- SAE cross-verification vs hospitalization/ConMed/labs; protocol-deviation flagging
- Escalates ALL SAE findings to human (Medical Monitor)

### CONMED-01 — ConMed Agent
*(implements REQ-conmed-verification, CON-coding-standards)*
- Verify ConMed entries vs records; start/stop date consistency
- ATC / WHO Drug Dictionary coding verification
- Prohibited-medication check vs exclusion criteria; drug-drug interaction screening
- Indication cross-reference vs Medical History and AE

### CONSIST-01 — Consistency Agent
*(implements REQ-cross-domain-consistency)*
- Matrix-based cross-domain verification across all domain pairs (MedHistory↔AE/SAE,
  MedHistory↔ConMed, MedHistory↔Labs, AE/SAE↔Labs, AE/SAE↔ConMed, AE/SAE↔Vitals,
  Labs↔ConMed, InformedConsent↔All Procedures)
- Surface clinically significant inconsistencies as queries

---

## Workflow Agents

### QUERY-01 — Query Agent
*(implements REQ-query-management)*
- Automated query generation with structured, protocol-specific language
- Priority classification (Critical/High/Medium/Low)
- Discrepancy-note lifecycle against the Rave **mock**; routing by query type
- Response evaluation, automated follow-up, escalation on thresholds
- Query metrics/KPIs by site, investigator, domain

### RISK-01 — Risk Agent
*(implements REQ-risk-based-scoring)*
- Risk-based site scoring drives monitoring prioritization (ICH E6(R3) RBM)
- Human escalation on risk score >7/10 or sudden risk changes

### REPORT-01 — Report Agent
*(implements REQ-reporting)*
- Generate SDV reports and visit letters from verification results
- Escalate regulatory-submission reports to human review
- (eTMF filing is deferred — eTMF integration out of this milestone)

---

## Portals & Review UI

### PORTAL-01 — CRA + Sponsor portals and audit-trail review UI
*(completes REQ-multi-tenancy-scale; React + TS)*
- CRA portal: full SDV workflow (review discrepancies, queries, agent findings)
- Sponsor portal: read-only dashboard
- Audit-trail review UI (EMA Annex 11 audit-trail review capability)
- Role-based UI surfaces for the 8 defined roles; multi-language-ready
- Human-in-the-loop approval surfaces wired to agent escalations

---

## Deferred (out of this milestone)

- **REQ-etmf-integration** — eTMF integration (Veeva Vault TMF, Montrium, Wingspan).
  Deferred to a future milestone.
- Additional eCRFs (Veeva EDC / Oracle Inform / REDCap); Japan/Brazil/Middle-East EMR
  adapters; enterprise / white-label tier; ISO 27001 cert; multi-region rollout; China
  isolated instance; predictive analytics; AI model fine-tuning.

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLAT-01 | Phase 1 | Complete |
| PLAT-02 | Phase 1 | Complete |
| PLAT-03 | Phase 1 | In Progress (PII field-encryption + pseudonymization done in 01-03; RBAC/MFA/tenancy in 01-04) |
| EMR-01 | Phase 2 | Pending |
| RAVE-01 | Phase 3 | Pending |
| AGENT-00 | Phase 4 | Pending |
| SDV-01 | Phase 5 | Pending |
| ALCOA-01 | Phase 5 | Pending |
| LAB-01 | Phase 5 | Pending |
| AESAE-01 | Phase 5 | Pending |
| CONMED-01 | Phase 5 | Pending |
| CONSIST-01 | Phase 5 | Pending |
| QUERY-01 | Phase 6 | Pending |
| RISK-01 | Phase 6 | Pending |
| REPORT-01 | Phase 6 | Pending |
| PORTAL-01 | Phase 7 | Pending |

**Coverage:** 16/16 milestone requirements mapped. No orphans. No duplicates.
REQ-etmf-integration intentionally deferred (out of scope).
