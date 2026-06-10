# Requirements Intel

Extracted from classified PRDs. One entry per requirement, with provenance.
Acceptance criteria are derived from the source document's stated behaviors and tables.

---

## REQ-sdv-engine — Source Data Verification Engine

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 2.1)
scope: Field-level comparison of EMR source data vs. Medidata Rave eCRF data.

Description: The core SDV engine performs field-level comparison between data
extracted from EMR source documents and data entered in Medidata Rave eCRF.

Acceptance criteria:
- Exact value matching for numerical data (lab values, vital signs, dates)
- Semantic matching for clinical terminology using SNOMED CT and MedDRA mappings
- Unit conversion and normalization (e.g., mg/dL ↔ mmol/L, Fahrenheit ↔ Celsius)
- Date format normalization across regional conventions
- Multi-language text comparison for international sites
- Handling of missing, partial, or illegible source data with appropriate flagging

---

## REQ-alcoa-compliance — ALCOA+ Compliance Verification

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 2.2)
scope: Assess every ingested source document against the 9 ALCOA+ principles
(FDA / ICH framework).

Description: Every source document ingested by the system must be assessed
against the ALCOA+ framework, with a defined verification method and failure
output per principle.

Acceptance criteria (per ALCOA+ principle):
- Attributable: detect author signature, credentials, date/time → query on missing attribution
- Legible: OCR confidence scoring, handwriting detection, image quality → flag for human review if score <95%
- Contemporaneous: compare document timestamp vs. event date with configurable windows → query on delayed documentation
- Original: document fingerprinting, hash verification, version control → flag potential uncertified copy
- Accurate: detect corrections without initials/date/reason, physiological plausibility → query on non-compliant correction
- Complete: protocol-driven per-visit checklist, mandatory field verification → query on missing documentation
- Consistent: cross-document consistency across visits and domains → query on inconsistency
- Enduring: file format and storage medium validation → alert on non-durable format
- Available: accessibility check at audit-simulation time → alert if document not retrievable

---

## REQ-lab-data-management — Laboratory Data Management

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 2.3)
scope: Multi-level lab result extraction, verification, and clinical significance.

Description: The laboratory module extracts, normalizes, verifies, and assesses
lab data from EMR sources against eCRF entries.

Acceptance criteria:
- Extraction and normalization of lab results from EMR using LOINC coding
- Verification of values, units, collection dates, and methods against eCRF
- Reference range comparison using site-specific certified laboratory normals
- Grade classification per CTCAE v5.0 (oncology) or NCI criteria
- Clinical significance assessment with three-tier alert (Low / Moderate / Critical)
- Trend analysis across visits with progressive-worsening detection
- Protocol-specific threshold monitoring (e.g., neutrophil counts, liver enzymes)
- Automatic cross-reference of clinically significant lab findings vs. AE/SAE reporting

---

## REQ-ae-sae-verification — Adverse Event and SAE Verification

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 2.4)
scope: Comprehensive monitoring and verification of safety data with regulatory
timeline tracking.

Description: The AE/SAE module verifies safety data completeness, grading,
causality, and regulatory reporting timelines.

Acceptance criteria:
- All AEs in source are recorded in eCRF (completeness check)
- CTCAE grade verification against source documentation narrative
- Start date, end date, and outcome consistency checks
- Causality assessment verification (related / not related) supported by documentation
- SAE regulatory timeline monitoring: 7-day (fatal/life-threatening) and 15-day (other) reporting windows for FDA and EMA
- SAE cross-verification against hospitalization records, concomitant medications, lab data
- Protocol Deviation flagging for unreported or late-reported SAEs

---

## REQ-conmed-verification — Concomitant Medication Verification

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 2.5)
scope: Verify ConMed entries against records and screen for interactions/prohibitions.

Description: The ConMed module verifies medication entries against source records
and screens for prohibited medications and interactions.

Acceptance criteria:
- Verification of all ConMed entries against medical records and prescription documentation
- Start/stop date consistency with medical history and AE documentation
- ATC / WHO Drug Dictionary coding verification
- Prohibited medication check against protocol exclusion criteria
- Drug-drug interaction screening with the investigational product
- Indication cross-reference with Medical History and AE data

---

## REQ-cross-domain-consistency — Cross-Domain Consistency Checks

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 2.6)
scope: Matrix-based cross-verification across all data domains.

Description: The Consistency Agent performs matrix-based cross-verification across
data domains, identifying clinically significant inconsistencies.

Acceptance criteria (domain-pair checks):
- Medical History ↔ AE/SAE: pre-existing condition worsening; baseline vs. new onset
- Medical History ↔ ConMed: documented diagnosis has corresponding medication or documented reason for absence
- Medical History ↔ Labs: diagnoses (e.g., diabetes) correspond to relevant lab assessments
- AE/SAE ↔ Labs: AE supported by lab evidence (e.g., nephrotoxicity ↔ creatinine elevation); grade matches severity
- AE/SAE ↔ ConMed: AE treatment documented as concomitant medication
- AE/SAE ↔ Vitals: AE (e.g., hypotension) corresponds to documented BP values
- Labs ↔ ConMed: dose modifications for toxicity trigger review of subsequent lab values
- Informed Consent ↔ All Procedures: consent date must precede all study procedures

---

## REQ-query-management — Query Management

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 2.7)
scope: Full automated query lifecycle within Medidata Rave.

Description: The Query Agent automates query generation, routing, evaluation, and
escalation directly within Medidata Rave.

Acceptance criteria:
- Automated query generation with structured, protocol-specific language
- Priority classification: Critical / High / Medium / Low
- Direct integration with Medidata Rave Discrepancy Note system via API
- Query routing to appropriate site personnel based on query type
- Response evaluation: assess whether a response resolves the query
- Automated follow-up for unresolved or unsatisfactory responses
- Escalation workflow for queries unanswered beyond configurable thresholds
- Query metrics and KPI tracking by site, investigator, and data domain

---

## REQ-risk-based-scoring — Risk-Based Site Scoring and Prioritization

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections 1.2, 3.2 Risk Agent)
scope: Site risk scoring and monitoring prioritization aligned with ICH E6(R3) RBM.

Description: Risk-based site scoring and monitoring prioritization, aligned with
ICH E6(R3) risk-based monitoring principles.

Acceptance criteria:
- Risk-based site scoring drives monitoring prioritization
- Human escalation triggered on risk score >7/10 or sudden risk changes
- Alignment with ICH E6(R3) RBM principles built into platform logic

---

## REQ-audit-trail — Regulatory-Compliant Audit Trail

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections 1.2, 4.3)
scope: Complete, secure, unalterable audit trail compliant with 21 CFR Part 11 and EMA Annex 11.
Note: retention and immutability are also captured as constraints (see constraints.md CON-audit-trail).

Description: All system actions must be captured in a complete, secure, and
unalterable audit trail.

Acceptance criteria:
- User identity, role, and access timestamp for every system interaction
- All data accessed/modified/deleted captured with before/after values
- All queries generated, modified, and closed with rationale
- All AI agent decisions captured with supporting evidence and confidence scores
- All system configuration changes captured
- All login attempts (successful and failed) captured

---

## REQ-emr-integration — EMR Integration Framework

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 3.3)
scope: Universal EMR Connector Framework with FHIR R4 normalization and fallback paths.
Note: FHIR R4 normalization is also an authoritative technical decision (see constraints.md CON-fhir-normalization).

Description: The Universal EMR Connector Framework provides adapters for major EMR
systems plus a fallback pathway for non-standard systems; all data normalized to
the FHIR R4 Unified Patient Data Model before processing.

Acceptance criteria:
- Native FHIR R4 for Epic, Cerner, Oracle Health, NHS SPINE (Patient, Encounter, Observation, Condition, MedicationRequest, AdverseEvent, DiagnosticReport, DocumentReference, Procedure)
- HL7 v2.x adapter (older hospital systems, Siemens, Agfa) mapped to FHIR via translation layer
- Proprietary API adapters for country-specific EMR systems with FHIR normalization
- Semi-manual import (structured PDF/Excel with AI extraction) for systems without API access
- Document OCR (paper/scanned) with OCR + NLP extraction to FHIR DocumentReference

---

## REQ-rave-integration — Medidata Rave eCRF Integration

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 3.4)
scope: Bidirectional integration with Medidata Rave via MDRWS API.
Note: Medidata Technology Partner status is a hard prerequisite (see constraints.md CON-medidata-partner).

Description: Medidata Rave is the primary eCRF integration target, using the
Medidata Rave Web Services (MDRWS) API for bidirectional data exchange.

Acceptance criteria:
- READ: subject data, CRF field values with audit trail, query status, protocol deviations, randomization data, freeze/lock status
- WRITE: open discrepancy notes (queries), update query status, set per-field SDV flags, flag protocol deviations
- WEBHOOKS: real-time triggers on new data entry, SAE submission, query response

---

## REQ-etmf-integration — eTMF Integration

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections 1.2, 5 Phase 2)
scope: Integration with eTMF systems (Veeva Vault TMF, Montrium, Wingspan).
Note: classified as Phase 2 in roadmap; in-scope overall but post-MVP.

Description: Integration with electronic Trial Master File systems for report and
document filing.

Acceptance criteria:
- Integrate with Veeva Vault TMF, Montrium, and Wingspan
- Report Agent files SDV reports and visit letters to eTMF via eTMF API

---

## REQ-reporting — SDV Reporting and Document Generation

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 3.2 Report Agent)
scope: Generation of SDV reports, visit letters, and eTMF filings.

Description: The Report Agent generates SDV reports, visit letters, and eTMF
filings from verification results.

Acceptance criteria:
- Generate SDV reports and visit letters
- File reports to eTMF
- Escalate regulatory submission reports to human review

---

## REQ-multi-agent-orchestration — Multi-Agent AI Architecture

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 3.2)
scope: Orchestrator Agent coordinating 10 specialized AI agents.
Note: per-agent human-escalation triggers are also captured as constraints (see constraints.md CON-human-in-the-loop).

Description: The platform deploys 10 specialized AI agents coordinated by an
Orchestrator Agent; each agent is an autonomous, stateful unit with defined
tools, decision logic, and escalation pathways.

Acceptance criteria:
- Orchestrator coordinates task planning, agent coordination, priority management; escalates conflicting findings across agents
- 10 specialized agents: SDV, ALCOA+, Lab, AE/SAE, ConMed, Consistency, Query, Risk, Report (plus Orchestrator)
- Each agent has defined tools, decision logic, and a human-escalation trigger
- Parallel, continuous monitoring rather than periodic review

---

## REQ-multi-tenancy-scale — Multi-Site, Multi-Study Global Deployment

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections 1.2, 3.1)
scope: Multi-site, multi-study, global deployment capability.
Note: regional data-residency is an authoritative constraint (see constraints.md CON-data-residency).

Description: The platform must support multi-site, multi-study, global deployment
across any number of sites, studies, and geographies.

Acceptance criteria:
- Multi-site, multi-study, global deployment capability
- Multi-language support for documentation and queries
- Regional cloud deployment to meet data residency requirements
- Role-based access for 8 defined user roles (see context.md: target users)

---

## Out of Scope (Phase 1)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 1.2)

Explicitly excluded from Phase 1:
- Electronic data capture (eCRF) — integration only, not replacement
- CTMS functionality
- Pharmacovigilance database submission (MedWatch, EudraVigilance)
- Direct patient-facing interfaces
- Statistical analysis plan execution
- Biostatistics or data management functions
