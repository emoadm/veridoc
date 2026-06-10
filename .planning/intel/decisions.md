# Decisions Intel

One entry per ADR (title, source, status, decision statement, scope).

No formal ADR documents were present in this ingest set (0 ADRs classified).

However, the single classified PRD embeds several **effectively-locked technical
and regulatory decisions** (flagged by the classifier). These are NOT formal
locked ADRs and therefore do NOT carry hard-BLOCKER LOCKED-vs-LOCKED semantics,
but downstream planning should treat them as authoritative for this project.
Recorded here as `status: embedded-authoritative (PRD-derived, not a formal ADR)`
for traceability. Full detail lives in constraints.md.

---

## DEC-fhir-r4-canonical — FHIR R4 as canonical patient data model

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 3.3)
status: embedded-authoritative (PRD-derived, not a formal ADR)
scope: internal data model / EMR normalization
statement: All EMR data is normalized to the FHIR R4 Unified Patient Data Model
before processing. See constraints.md CON-fhir-normalization.

---

## DEC-rave-primary-ecrf — Medidata Rave is the primary eCRF

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections "Proposed Solution", 3.4)
status: embedded-authoritative (PRD-derived, not a formal ADR)
scope: eCRF integration target
statement: Medidata Rave (via MDRWS API) is the primary eCRF integration target;
other eCRFs are deferred to Phase 2. See constraints.md CON-rave-primary-ecrf.

---

## DEC-human-in-the-loop — Mandatory human-in-the-loop for clinical decisions

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections "Critical Success Factors" #5, 4.4)
status: embedded-authoritative (PRD-derived, not a formal ADR)
scope: AI decision architecture
statement: VeriDoc AI is a decision-support tool; all clinical decisions require
qualified human review and approval. See constraints.md CON-human-in-the-loop.

---

## DEC-gamp5-csv — GAMP 5 CSV lifecycle

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 4.2)
status: embedded-authoritative (PRD-derived, not a formal ADR)
scope: validation methodology
statement: Computer System Validation follows the GAMP 5 framework; IQ/OQ/PQ
required before commercial deployment. See constraints.md CON-gamp5-csv and
CON-iq-oq-pq-validation.

---

## DEC-regional-data-residency — Regional cloud data residency

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (sections 3.1, 3.5)
status: embedded-authoritative (PRD-derived, not a formal ADR)
scope: deployment topology / data residency
statement: Regional cloud instances (Americas/EMEA/APAC + isolated China) are
required from day one. See constraints.md CON-data-residency.

---

## DEC-cloud-provider — Cloud infrastructure provider (UNDECIDED)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 8 Next Steps #4)
status: open (deferred decision)
scope: infrastructure
statement: Cloud provider selection (AWS or Azure) is explicitly deferred to an
early Next Step (#4), to be made "based on initial target market geography."
Architecture references both AWS and Azure components; this remains an open
decision for downstream planning, not a conflict.
