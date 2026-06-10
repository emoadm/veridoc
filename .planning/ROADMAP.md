# VeriDoc AI — Roadmap (Milestone 1: Buildable Phase-1 Core)

**Milestone goal:** The SDV engine, driven by the orchestrator + specialized agents,
ingests synthetic FHIR R4 EMR data and a Medidata Rave mock, performs field-level +
semantic comparison, and emits structured, prioritized discrepancy queries with
ALCOA+ assessment and a complete, tamper-evident audit trail — all verifiable
end-to-end against fixtures.

**Granularity:** Standard (no config.json present). Eight phases reflect the natural
dependency boundaries of the agent fleet, not arbitrary padding.

**Parallel constraints (tracked, not phases):** CON-regulatory-strategy-first,
CON-medidata-partner (Rave built against a mock), CON-iq-oq-pq-validation /
CON-gamp5-csv (validation-ready docs throughout; PQ + production gate *commercial*
deployment, not this build), CON-pilot-partner. See PROJECT.md.

## Phases

- [ ] **Phase 1: Platform Skeleton & Audit Foundation** - Monorepo, service scaffold, CI/CD, tamper-evident audit trail, and RBAC/identity baseline, all 21 CFR Part 11-ready.
- [ ] **Phase 2: FHIR R4 Model & EMR Ingestion** - Canonical FHIR R4 patient model and ingestion framework (synthetic FHIR, HL7 v2.x, semi-manual import, OCR).
- [ ] **Phase 3: Medidata Rave Mock Integration** - Bidirectional MDRWS integration behind an abstraction layer, exercised against a Rave mock.
- [ ] **Phase 4: Multi-Agent Framework & Orchestrator** - LangGraph framework, Orchestrator Agent, LLM engine, and human-in-the-loop gating.
- [ ] **Phase 5: Core Verification Agents** - SDV, ALCOA+, Lab, AE/SAE, ConMed, and Consistency agents producing discrepancies and ALCOA+ assessments.
- [ ] **Phase 6: Query, Risk & Report Agents** - Query lifecycle against the mock, risk-based site scoring, and SDV report/visit-letter generation.
- [ ] **Phase 7: CRA & Sponsor Portals + Audit Review UI** - React portals for the 8 roles and the audit-trail review interface; human-in-the-loop approval surfaces.
- [ ] **Phase 8: End-to-End Verification Against Fixtures** - Wire the full pipeline and prove the milestone success metric end-to-end on synthetic data.

## Phase Details

### Phase 1: Platform Skeleton & Audit Foundation
**Goal**: A running cloud-native scaffold where every action is captured in a
tamper-evident, 21 CFR Part 11-ready audit trail, and identity/roles exist for the
8 user types.
**Depends on**: Nothing (first phase)
**Requirements**: PLAT-01, PLAT-02, PLAT-03
**Success Criteria** (what must be TRUE):
  1. A developer can run the monorepo's backend + frontend scaffold locally and deploy it to a single Kubernetes cluster via the CI/CD pipeline (lint/test/build/deploy green).
  2. Every recorded system action produces an append-only, hash-chained audit record capturing identity, role, timestamp, and before/after values — and tampering with a prior record is detectable.
  3. A user can authenticate with one of the 8 defined roles, behind MFA, and only sees access permitted by that role.
  4. Patient-identifiable data is pseudonymized and field-level encrypted at rest; cloud-provider choice remains abstracted (DEC-cloud-provider open).
**Plans**: 6 plans in 4 waves
- [x] 01-01-PLAN.md — Monorepo scaffold (uv+pnpm), Taskfile, pytest+Vitest Wave 0 harness, package-legitimacy gate
- [x] 01-02-PLAN.md — veridoc-audit SDK: JCS canonicalization + same-transaction hash chain + tamper detection
- [ ] 01-03-PLAN.md — veridoc-crypto + veridoc-pseudonym: per-patient key hierarchy, envelope encryption, crypto-shred
- [ ] 01-04-PLAN.md — veridoc-auth + veridoc-tenancy: Keycloak realm-as-code, OIDC/MFA/8-role RBAC, fail-closed tenancy
- [ ] 01-05-PLAN.md — Reference service wired end-to-end (D-07 walking skeleton) + Dockerfile + integration tests
- [ ] 01-06-PLAN.md — Provider-portable Helm + Terraform + GitHub Actions CI deploying to ephemeral kind cluster

### Phase 2: FHIR R4 Model & EMR Ingestion
**Goal**: Heterogeneous EMR inputs are normalized into one canonical FHIR R4 patient
model, ready for agents to verify.
**Depends on**: Phase 1
**Requirements**: EMR-01
**Success Criteria** (what must be TRUE):
  1. Synthetic FHIR R4 EMR data loads into the Unified Patient Data Model (Patient, Encounter, Observation, Condition, MedicationRequest, AdverseEvent, DiagnosticReport, DocumentReference, Procedure) and is queryable.
  2. An HL7 v2.x message and a structured PDF/Excel import both normalize into the same FHIR R4 representation.
  3. A scanned/paper document is OCR + NLP extracted into a FHIR DocumentReference with an OCR confidence score attached.
  4. Patient-identifiable fields are pseudonymized at ingestion time.
**Plans**: TBD

### Phase 3: Medidata Rave Mock Integration
**Goal**: The platform can read eCRF data from, and write discrepancies/flags to, a
Medidata Rave mock through an abstraction layer that can later be swapped for the
production MDRWS API.
**Depends on**: Phase 1
**Requirements**: RAVE-01
**Success Criteria** (what must be TRUE):
  1. The system READs subject data, CRF field values (with audit trail), query status, protocol deviations, randomization, and freeze/lock status from the Rave mock.
  2. The system WRITEs a discrepancy note, updates query status, sets a per-field SDV flag, and flags a protocol deviation against the mock.
  3. A mock webhook (new data entry / SAE submission / query response) triggers the corresponding pipeline action.
  4. The MDRWS contract is isolated behind an abstraction layer, so swapping mock → production requires no agent-code changes.
**Plans**: TBD

### Phase 4: Multi-Agent Framework & Orchestrator
**Goal**: A LangGraph multi-agent runtime exists where stateful agents are coordinated
by an Orchestrator and every clinical decision is gated by mandatory human review.
**Depends on**: Phase 2, Phase 3
**Requirements**: AGENT-00
**Success Criteria** (what must be TRUE):
  1. The Orchestrator plans tasks, coordinates a stub agent, manages priority, and escalates a conflicting cross-agent finding to a human.
  2. Agents run in parallel/continuous mode (not periodic batch) against ingested FHIR + Rave-mock data.
  3. A simulated clinical decision is blocked from auto-action and routed to the correct human role per its escalation trigger.
  4. The LLM engine (Claude/GPT-4) returns structured outputs with confidence scores, and low-confidence outputs trigger conservative escalation.
**Plans**: TBD

### Phase 5: Core Verification Agents
**Goal**: The six core agents verify EMR-vs-eCRF data and assess source documents,
producing structured discrepancies and ALCOA+ assessments.
**Depends on**: Phase 4
**Requirements**: SDV-01, ALCOA-01, LAB-01, AESAE-01, CONMED-01, CONSIST-01
**Success Criteria** (what must be TRUE):
  1. The SDV Agent flags a value mismatch between FHIR source and the Rave mock using exact matching for numerics and SNOMED CT/MedDRA semantic matching for terminology, with unit and date normalization applied.
  2. The ALCOA+ Agent assesses an ingested document against all 9 principles and flags a sub-95% legibility document for human review (escalating below 85%).
  3. The Lab Agent grades a lab result per CTCAE v5.0 with LOINC coding, raises a 3-tier significance alert, and cross-references a significant finding against AE/SAE.
  4. The AE/SAE Agent detects a missing AE, verifies SAE reporting timelines (7-day/15-day), and escalates every SAE finding to the Medical Monitor; the ConMed Agent flags a prohibited medication via ATC/WHO Drug coding; the Consistency Agent surfaces a cross-domain inconsistency (e.g., AE not supported by lab evidence).
**Plans**: TBD

### Phase 6: Query, Risk & Report Agents
**Goal**: Verification findings become prioritized queries with a full lifecycle,
drive risk-based site scoring, and roll up into SDV reports.
**Depends on**: Phase 5
**Requirements**: QUERY-01, RISK-01, REPORT-01
**Success Criteria** (what must be TRUE):
  1. The Query Agent generates a structured, priority-classified (Critical/High/Medium/Low) query, opens it as a discrepancy note on the Rave mock, evaluates a response, and escalates on threshold breach.
  2. The Risk Agent computes a site risk score, prioritizes monitoring, and escalates to a human when score >7/10 or on a sudden change.
  3. The Report Agent generates an SDV report and a visit letter from verification results, and routes a regulatory-submission report to human review.
  4. Query metrics/KPIs are aggregated by site, investigator, and data domain.
**Plans**: TBD

### Phase 7: CRA & Sponsor Portals + Audit Review UI
**Goal**: Humans can review agent findings, act on the SDV workflow, approve gated
decisions, and inspect the audit trail through role-appropriate web UIs.
**Depends on**: Phase 6
**Requirements**: PORTAL-01
**Success Criteria** (what must be TRUE):
  1. A CRA can review discrepancies, queries, and agent findings, and approve a human-in-the-loop escalation through the CRA portal.
  2. A Sponsor representative sees a read-only dashboard of study/site status.
  3. A Regulatory Affairs user can browse and filter the immutable audit trail through the audit-review UI (EMA Annex 11 review capability).
  4. UI surfaces are role-gated for all 8 roles and rendered through a multi-language-ready React/TS frontend.
**Plans**: TBD
**UI hint**: yes

### Phase 8: End-to-End Verification Against Fixtures
**Goal**: The full milestone success metric is demonstrably true: synthetic FHIR +
Rave mock in, prioritized discrepancy queries + ALCOA+ assessment + complete audit
trail out — verifiable end-to-end.
**Depends on**: Phase 7
**Requirements**: (integration of PLAT-02, EMR-01, RAVE-01, AGENT-00, SDV-01, ALCOA-01, LAB-01, AESAE-01, CONMED-01, CONSIST-01, QUERY-01, RISK-01, REPORT-01, PORTAL-01)
**Success Criteria** (what must be TRUE):
  1. A single fixtured run ingests synthetic FHIR R4 EMR data and Rave-mock eCRF data, runs the orchestrated agent fleet, and emits prioritized discrepancy queries — reproducibly in CI.
  2. Each emitted discrepancy carries an ALCOA+ assessment and the agent decision (with confidence + evidence) is captured in the audit trail.
  3. The end-to-end audit trail for the run is complete and tamper-evident, traceable from ingestion through query emission.
  4. Every gated clinical decision in the run is shown awaiting the correct human role rather than auto-actioned.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Platform Skeleton & Audit Foundation | 2/6 | In Progress|  |
| 2. FHIR R4 Model & EMR Ingestion | 0/0 | Not started | - |
| 3. Medidata Rave Mock Integration | 0/0 | Not started | - |
| 4. Multi-Agent Framework & Orchestrator | 0/0 | Not started | - |
| 5. Core Verification Agents | 0/0 | Not started | - |
| 6. Query, Risk & Report Agents | 0/0 | Not started | - |
| 7. CRA & Sponsor Portals + Audit Review UI | 0/0 | Not started | - |
| 8. End-to-End Verification Against Fixtures | 0/0 | Not started | - |
