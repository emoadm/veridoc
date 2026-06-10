# Constraints Intel

Technical and regulatory constraints extracted from the source document. The PID
is a hybrid Project Initiation Document; section 3 carries SPEC-level technical
architecture and sections 4–8 carry regulatory prerequisites. Several of these are
effectively-locked decisions/prerequisites embedded in a PRD-classified document
(see classifier notes) — surfaced here so downstream planning treats them as
binding rather than optional.

Constraint types: api-contract | schema | nfr | protocol | regulatory-prerequisite

---

## CON-regulatory-strategy-first — Regulatory Affairs strategy before development

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections "Critical Success Factors" #1, 8 Next Steps #1)
type: regulatory-prerequisite

A Regulatory Affairs strategy (21 CFR Part 11, EMA Annex 11, ICH E6(R3)) must be
established BEFORE development begins. Next Steps #1 (Critical): engage a Regulatory
Affairs consultant with 21 CFR Part 11 and EMA Annex 11 experience to develop the
regulatory strategy and CSV plan before any development begins. This is a hard
sequencing prerequisite — development cannot start until this gate is cleared.

---

## CON-medidata-partner — Official Medidata Technology Partner status

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections "Critical Success Factors" #3, 3.4, 8 Next Steps #3, Risk Register)
type: regulatory-prerequisite

Official Medidata Technology Partner status must be obtained to secure full Rave
API documentation, support, and production API access. Production Rave integration
(MDRWS API, webhooks, discrepancy notes) is GATED on this partner agreement.
Risk register mitigation: pursue formal Technology Partner agreement; build an
abstraction layer for API versioning; maintain direct eCRF import as fallback.

---

## CON-iq-oq-pq-validation — IQ/OQ/PQ system validation before commercial deployment

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections "Critical Success Factors" #4, 4.2)
type: regulatory-prerequisite

System validation (IQ/OQ/PQ) must be completed before commercial deployment.
VeriDoc AI requires formal Computer System Validation (CSV) before use in any
clinical trial, following the GAMP 5 framework lifecycle:
- URS — documented functional and non-functional requirements traceable to regulatory standards
- FS — detailed specification of system functions and behaviors
- DQ — verification that system design meets specified requirements
- IQ — verification that the system is installed correctly in the target environment
- OQ — verification that the system operates as specified throughout operational ranges
- PQ — verification that the system performs consistently in the intended-use environment
- Ongoing Validation — change control, periodic review, revalidation on significant change

Sequencing: IQ/OQ begin in Phase 1 (M12); PQ completion is a Phase 2 deliverable
(prior to commercial deployment and FDA/EMA submissions).

---

## CON-human-in-the-loop — Mandatory human-in-the-loop for all clinical decisions

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections "Critical Success Factors" #5, 4.4, 3.2)
type: regulatory-prerequisite

VeriDoc AI operates as a decision-support tool only. Human-in-the-loop
architecture must be maintained for ALL clinical decisions. The following
decisions require qualified human review and approval before any action:
- SAE causality assessment → Medical Monitor (physician)
- Protocol Deviation determination → CRA + Medical Monitor
- Clinical significance of laboratory findings → Medical Monitor
- Query closure for complex clinical disputes → Senior CRA / Medical Monitor
- Site escalation recommendations → Clinical Operations Lead
- Regulatory reporting decisions → Regulatory Affairs + Medical Monitor
- Study halt or suspension recommendations → Sponsor Medical Officer

Each of the 10 AI agents additionally carries a defined human-escalation trigger
(section 3.2), e.g. ALCOA+ Agent escalates on legibility <85% or fraud indicators;
AE/SAE Agent escalates on ALL SAE findings; Lab Agent on critical values / Grade 3+.
This is a binding architectural constraint, not a configurable option.

---

## CON-pilot-partner — Pilot CRO/Sponsor partner during design phase

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections "Critical Success Factors" #2, 8 Next Steps #2)
type: regulatory-prerequisite

At least one CRO or Sponsor pilot partner must be engaged during the design phase.
Next Steps #2 (Critical): identify and approach 2–3 potential pilot CRO/Sponsor
clients; negotiate a pilot agreement including co-development input and reference
rights. This is a business prerequisite for real-world validation in Phase 1.

---

## CON-fhir-normalization — FHIR R4 Unified Patient Data Model (canonical model)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 3.3)
type: schema

All EMR data must be normalized to the FHIR R4 Unified Patient Data Model before
processing. FHIR R4 is the canonical internal representation; HL7 v2.x, proprietary
APIs, semi-manual imports, and OCR all map into FHIR R4 (DocumentReference, etc.).
Effectively-locked technical decision embedded in the PID.

---

## CON-source-heterogeneity — Per-site source-document modality varies (paper vs EMR vs mixed)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections 1.1, 2.1, 3.3) + user clarification (2026-06-10)
type: schema

Different clinical centers use different source documents. Some sites are EMR-based,
some maintain paper/scanned source documents only, and some are mixed. The platform
must NOT assume a single source modality. Implications:
- A site's source profile (EMR / paper / mixed + applicable ingestion path) is a
  configurable, first-class property per site.
- Every ingestion path (native FHIR R4, HL7 v2.x, proprietary API, semi-manual
  PDF/Excel, paper/scanned OCR) normalizes to the SAME canonical FHIR R4 model
  (see CON-fhir-normalization) so that all downstream verification is source-agnostic.
- Provenance (source modality + ingestion path) is recorded on every ingested unit.
  Paper-derived data carries OCR confidence and triggers ALCOA+ legibility scoring;
  illegible/low-confidence fields are flagged for human review.
This is a binding architectural constraint: the ingestion layer absorbs source
heterogeneity so the agent fleet sees one uniform data model. Tracked functionally
as REQ-emr-integration / EMR-01.

---

## CON-rave-primary-ecrf — Medidata Rave as primary eCRF (MDRWS API contract)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections "Proposed Solution", 3.4)
type: api-contract

Medidata Rave is the primary eCRF integration target via the Medidata Rave Web
Services (MDRWS) API. Bidirectional contract:
- READ: subject data, CRF field values with audit trail, query status, protocol deviations, randomization, freeze/lock status
- WRITE: open discrepancy notes, update query status, set per-field SDV flags, flag protocol deviations
- WEBHOOKS: new data entry, SAE submission, query response
Effectively-locked decision (primary eCRF). Other eCRFs (Veeva EDC, Oracle Inform,
REDCap) are deferred to Phase 2; platform positioning is eCRF-agnostic long-term.

---

## CON-gamp5-csv — GAMP 5 Computer System Validation

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 4.2)
type: protocol

CSV must follow the GAMP 5 framework (URS → FS → DQ → IQ → OQ → PQ → Ongoing
Validation). Validation-ready documentation must be produced throughout
development. See CON-iq-oq-pq-validation for the deployment gate.

---

## CON-data-residency — Regional data residency and cloud isolation

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections 3.1, 3.5)
type: nfr

Regional cloud instances are required to meet data residency requirements:
- Americas: AWS us-east
- EMEA: Azure West Europe
- APAC: AWS ap-southeast
- China: isolated instance
Regional deployment from day one (risk register mitigation); GDPR and PIPL
compliance by design. Effectively-locked architectural constraint.

---

## CON-audit-trail — Immutable audit trail with 15-year retention

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 4.3)
type: nfr

Audit trail must be complete, secure, and unalterable (immutable). Audit trail
data must be retained for a minimum of 15 years post-study completion, or as
required by the longest applicable regulatory retention period. Captures user
identity/role/timestamp, before/after data values, query lifecycle with rationale,
AI agent decisions with evidence and confidence scores, configuration changes, and
all login attempts. (Functional capture obligations also tracked as REQ-audit-trail.)

---

## CON-security-compliance — Security and compliance controls (21 CFR Part 11 / Annex 11 / GDPR / HIPAA / ISO 27001)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 3.5)
type: nfr

- 21 CFR Part 11: electronic signatures with biometric confirmation; complete time-stamped audit trail; access controls; validated system status
- EMA Annex 11: change control; data integrity controls; backup and recovery; audit trail review capability
- GDPR Article 9: pseudonymization of patient-identifiable data at ingestion; data residency enforcement; consent management; right-to-erasure workflow
- HIPAA / HITECH: PHI encryption at rest (AES-256) and in transit (TLS 1.3); access controls; breach notification
- ISO 27001: ISMS; risk assessment; security incident management (certification targeted Phase 2)
- Encryption: AES-256 at rest; TLS 1.3 in transit; HSM key management; field-level encryption for PII
- Access Control: RBAC; MFA; session management; IP allowlisting for site access

---

## CON-applicable-regulations — Applicable regulatory frameworks

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 4.1)
type: regulatory-prerequisite

The system must comply with: ICH E6(R3), ICH E8(R1), FDA 21 CFR Part 11, FDA 21
CFR Part 312, EMA Annex 11, EU Regulation 536/2014, PMDA ERES Guidelines (Japan),
NMPA Clinical Trial Data Management Guidelines (China), ANVISA RDC 204/2017 (Brazil).
Non-EU/US frameworks (PMDA, NMPA, ANVISA) align with Phase 2/3 geographic expansion.

---

## CON-coding-standards — Required clinical coding standards

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections 2.1, 2.3, 2.4, 2.5)
type: protocol

The platform must use the following standard terminologies/codings:
- SNOMED CT and MedDRA — semantic clinical terminology matching
- LOINC — laboratory result coding
- CTCAE v5.0 / NCI criteria — lab and AE grading
- ATC / WHO Drug Dictionary — concomitant medication coding
These are binding interoperability constraints for verification correctness.
