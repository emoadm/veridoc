## Conflict Detection Report

Mode: new
Sources ingested: 1 PRD
Cross-ref graph: empty (cross_refs: []) — cycle detection ran, no cycles, depth 0.

### BLOCKERS (0)

None. No LOCKED-vs-LOCKED contradictions (0 formal ADRs), no UNKNOWN/low-confidence
docs, no cross-ref cycles, no existing locked context (fresh project, new mode).

### WARNINGS (0)

None. Only one source document was ingested, so there are no competing acceptance
variants across PRDs and no cross-document contradictions to resolve.

### INFO (3)

[INFO] Embedded authoritative decisions inside a PRD-classified document
  Found: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md carries several
    effectively-locked technical/regulatory decisions despite PRD classification:
    FHIR R4 canonical model (section 3.3), Medidata Rave as primary eCRF
    (section 3.4), mandatory human-in-the-loop (sections 4.4 / Critical Success
    Factors #5), GAMP 5 CSV (section 4.2), regional data residency (sections 3.1/3.5).
  Note: These are recorded in decisions.md as `embedded-authoritative (PRD-derived,
    not a formal ADR)` and detailed in constraints.md. They do NOT carry hard
    LOCKED-vs-LOCKED semantics (no formal locked ADR exists), but downstream
    planning should treat them as binding for this project.

[INFO] Regulatory prerequisites captured as constraints, not requirements
  Found: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md states four hard
    prerequisites — Regulatory Affairs strategy before development begins (CSF #1,
    Next Steps #1), official Medidata Technology Partner status for production API
    access (CSF #3, sections 3.4 / Next Steps #3), IQ/OQ/PQ validation before
    commercial deployment (CSF #4, section 4.2), and mandatory human-in-the-loop
    for all clinical decisions (CSF #5, section 4.4).
  Note: Recorded as constraints CON-regulatory-strategy-first, CON-medidata-partner,
    CON-iq-oq-pq-validation, and CON-human-in-the-loop. These are sequencing/gating
    prerequisites the roadmapper must honor (e.g., production Rave integration is
    gated on partner status; commercial deployment is gated on IQ/OQ/PQ).

[INFO] One explicitly deferred decision (not a conflict)
  Found: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (Next Steps #4)
    defers cloud provider selection (AWS or Azure) "based on initial target market
    geography"; the architecture (section 3.1) references both AWS and Azure
    components.
  Note: Recorded in decisions.md as DEC-cloud-provider status:open. This is an
    intentional open decision for downstream planning, not a contradiction.
