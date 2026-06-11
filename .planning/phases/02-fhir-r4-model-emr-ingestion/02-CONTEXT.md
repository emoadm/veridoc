# Phase 2: FHIR R4 Model & EMR Ingestion - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Normalize heterogeneous EMR inputs into ONE canonical **FHIR R4 Unified Patient Data
Model** so the agent fleet (Phases 4–6) sees a single, source-modality-agnostic
representation. Concretely this phase delivers:

- The canonical FHIR R4 model (Patient, Encounter, Observation, Condition,
  MedicationRequest, AdverseEvent, DiagnosticReport, DocumentReference, Procedure),
  loadable and queryable.
- An ingestion framework where **per-site source modality is a first-class,
  configurable property** that drives routing, with four working ingestion paths
  (native FHIR, HL7 v2.x, semi-manual PDF/Excel, paper/scanned OCR) all normalizing to
  the same FHIR R4 model.
- Per-unit provenance (source modality + ingestion path + OCR confidence) recorded on
  every ingested resource; paper-derived data carries OCR confidence and triggers
  ALCOA+ legibility flagging.
- Pseudonymization of patient-identifiable fields at ingestion time.

OUT of scope (own phases): Medidata Rave integration (Phase 3), the agent fleet incl.
the LLM engine and ALCOA+ *scoring agent* itself (Phases 4–6), portals (Phase 7).
This phase produces the data substrate those phases consume.

Locked, NOT re-decided here (carried from Phase 1 / project-level):
- **DEC-fhir-r4-canonical** — FHIR R4 is the canonical internal representation.
- **DEC-cloud-provider OPEN** → every engine/datastore choice (OCR, blob store) stays
  AWS/Azure-portable, mirroring the Phase 1 KMS abstraction.
- **D-10** — MongoDB + blob store were explicitly deferred to "the phase that first
  needs them (Phase 2 EMR ingestion / OCR)" — this phase stands them up.
- **D-07** — walking-skeleton pattern: shared `veridoc-*` libs + a thin service later
  phases clone.
- **D-12** — deterministic per-patient pseudonym tokens (`veridoc-pseudonym`) are the
  pseudonymization mechanism; reuse, don't reinvent.
- **D-05** — services write to the audit trail through the shared `veridoc-audit` SDK.

</domain>

<decisions>
## Implementation Decisions

### FHIR model & storage
- **D-01:** The canonical FHIR R4 model uses the **`fhir.resources`** library
  (Pydantic v2 FHIR R4 resource models with full spec validation) for the 9 resource
  types — not hand-rolled models. Subject to `docs/validation/PACKAGE-LEGITIMACY.md`
  vetting before adoption.
- **D-02:** Canonical FHIR data persists in **MongoDB** (document store), standing up
  the datastore deferred in D-10. FHIR resources are JSON documents; the store is
  queryable by resource type / patient. (Postgres remains the audit/identity/tenancy
  store; Mongo is the new clinical-document store.)
- **D-03:** Provenance is modeled **spec-natively** via the **FHIR `Provenance`
  resource + `resource.meta` (`meta.source`)** — capturing source modality, ingestion
  path, and OCR confidence inside the FHIR model so downstream agents and ALCOA+
  legibility scoring read it uniformly. (Not a separate sidecar table.)

### Ingestion architecture
- **D-04:** Packaged per the walking-skeleton pattern (D-07): a **`veridoc-fhir`** lib
  (canonical model + repository) and a **`veridoc-ingestion`** lib (adapter interface +
  adapters), consumed by a thin **`services/ingestion-service`** cloned from
  `reference-service`. The libs are reusable by the agent fleet in later phases.
- **D-05:** Per-site routing uses a configurable **`SourceProfile` registry** (EMR /
  paper / mixed + applicable path, per site) selecting from a single **`SourceAdapter`
  interface** with N implementations. The SourceProfile is the first-class config that
  absorbs source heterogeneity (CON-source-heterogeneity).
- **D-06:** Ingestion is **asynchronous** — a Redis-backed queue (Redis is already in
  the stack from Phase 1) decouples slow OCR/extraction from the request path.
  Provenance and audit writes are recorded as jobs progress. *(This is a deliberate
  deviation from the Phase 1 synchronous-audit default D-05: OCR latency justifies a
  job queue here; the audit write for each completed ingest still goes through the
  shared `veridoc-audit` SDK.)*

### OCR + NLP extraction (paper/scanned path)
- **D-07:** OCR runs behind a **portable `OcrEngine` abstraction** (mirroring the
  Phase 1 KMS abstraction) so no cloud provider is bound while DEC-cloud-provider is
  open; swappable to Textract/Azure DI later.
- **D-08:** The OSS default engine is **Tesseract** — battle-tested, easily packaged,
  emits per-token confidence; sufficient for fixture-driven verification this
  milestone. The abstraction allows swapping to docTR/PaddleOCR/cloud later.
- **D-09:** The scanned path produces a **FHIR `DocumentReference` with an OCR
  confidence score** + ALCOA+ legibility flags (flag <95%, escalate <85%, per
  ALCOA-01). A **clinical-entity extraction interface** is defined (LLM-backable later,
  since the LLM engine lands in Phase 4) but this phase's extraction stays
  **minimal / rule-based** — it does not front-run Phase 4's LLM integration.
- **D-10:** Stand up a **portable S3-compatible blob store** (MinIO locally/CI,
  portable to S3 / Azure Blob) for original scanned documents; the `DocumentReference`
  points to the retained original (supports the ALCOA+ "Original" principle). Completes
  the D-10 blob-store deferral.

### Adapter scope / depth
- **D-11:** Build **four** paths fully — native FHIR, HL7 v2.x, semi-manual PDF/Excel,
  paper/scanned OCR (the four with success criteria). The **proprietary-API adapter is
  interface-only** (conforms to `SourceAdapter`, raises NotImplemented) — no real
  proprietary contract exists to test against this milestone.
- **D-12:** The HL7 v2.x path uses a **vetted library parser** (e.g. `hl7apy` /
  `python-hl7`, subject to PACKAGE-LEGITIMACY) + an **explicit mapping layer** to FHIR
  for the segments the fixtures exercise — not a hand-rolled parser.
- **D-13:** Native-path / synthetic FHIR test data is generated with **Synthea**
  (open-source synthetic patient generator) producing realistic FHIR R4 bundles,
  supplemented with hand-crafted edge cases. These fixtures are reusable by later
  phases' verification.

### Pseudonymization & audit at ingestion
- **D-14:** Patient-identifiable fields are pseudonymized **at ingestion time** by
  reusing **`veridoc-pseudonym`** (deterministic per-patient tokens, D-12) so the same
  patient maps consistently across sources — a prerequisite for later cross-source SDV
  matching. Every ingest writes through the shared **`veridoc-audit`** SDK.

### Claude's Discretion
- The semi-manual PDF/Excel path uses the **same rule-based extraction interface** as
  the OCR path (structure-aware extraction → FHIR); exact extraction rules are
  planner/researcher's call.
- Exact `SourceAdapter` interface shape, queue/worker mechanism (e.g. RQ vs Celery vs
  custom Redis consumer), Mongo collection/index design, and the `OcrEngine` interface
  signature — planner/researcher choose, consistent with the decisions above.
- Which precise FHIR resources each non-native adapter emits beyond what the success
  criteria mandate.

</decisions>

<specifics>
## Specific Ideas

- The ingestion layer is the seam that "absorbs source heterogeneity so the agent fleet
  sees one uniform data model" (CON-source-heterogeneity). Adapters differ; everything
  downstream of the FHIR model is source-agnostic.
- Keep every external dependency swappable like Phase 1's abstractions: OCR engine and
  blob store both stay provider-portable (DEC-cloud-provider open).
- Provenance + OCR confidence must be present on ingested units now, because ALCOA-01
  (Phase 5) consumes them for legibility scoring — don't defer the metadata.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Primary spec
- `docs/prd/veridoc-pid.md` §3.3 — FHIR R4 Unified Patient Data Model / FHIR
  normalization. §1.1, 2.1, 3.3 — per-site source heterogeneity (paper vs EMR vs mixed).

### Requirements & constraints
- `.planning/REQUIREMENTS.md` §Data Ingestion & Integration — **EMR-01** (the
  acceptance-level detail this phase implements: 9 resource types, configurable per-site
  source modality, 5 ingestion paths, provenance, OCR confidence, pseudonymization).
- `.planning/intel/constraints.md` — **CON-fhir-normalization** (canonical FHIR R4
  model) and **CON-source-heterogeneity** (per-site modality is a first-class
  configurable property; ingestion layer absorbs heterogeneity).
- `.planning/PROJECT.md` — **DEC-fhir-r4-canonical** (locked), **DEC-cloud-provider
  OPEN** (portability constraint), security/GDPR Art. 9 ingestion-time pseudonymization.

### Phase 1 foundation to reuse (read before adding anything new)
- `.planning/phases/01-platform-skeleton-audit-foundation/01-CONTEXT.md` — D-07
  (walking skeleton), D-10 (Mongo/blob deferred to here), D-11/D-12 (crypto +
  deterministic pseudonym tokens), D-05 (synchronous audit SDK).
- `libs/veridoc-pseudonym/` — deterministic per-patient pseudonymization (reuse, D-14).
- `libs/veridoc-audit/` — shared audit SDK (every ingest writes through it).
- `libs/veridoc-crypto/` — envelope encryption / KMS abstraction (the portability
  pattern OCR + blob store mirror).
- `services/reference-service/` — the template `ingestion-service` is cloned from.

### Dependency governance (MANDATORY before adopting any new package)
- `docs/validation/PACKAGE-LEGITIMACY.md` — all new deps (`fhir.resources`, the HL7
  parser, Tesseract bindings, Synthea tooling, MongoDB driver, blob/MinIO client) must
  be vetted/APPROVED here before use.

No formal ADRs exist yet; the PID is embedded-authoritative.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `libs/veridoc-pseudonym` — deterministic per-patient tokens; the pseudonymization
  mechanism for D-14 (ingestion-time PII handling).
- `libs/veridoc-audit` — shared audit SDK; ingestion writes audit records through it.
- `libs/veridoc-crypto` — envelope encryption + KMS abstraction; the portability
  pattern the new `OcrEngine` and blob-store abstractions follow.
- `services/reference-service` (uv workspace member: `src/reference_service/` with
  `main.py`, `config.py`, `db.py`, `models.py`, `migrate.py`, `api/`) — the clone
  template for `services/ingestion-service`.

### Established Patterns
- uv workspace monorepo (`pyproject.toml` `[tool.uv.workspace]`, members `libs/*` +
  `services/*`); new libs `veridoc-fhir` / `veridoc-ingestion` register the same way.
- Per-language tooling (uv + ruff + pytest; `testpaths = ["libs","services"]`,
  `--import-mode=importlib`). New packages follow the `src/<pkg>/` + `tests/` layout.
- Phase 1 stack is **Postgres + Redis only**; this phase adds **MongoDB** (D-02) and a
  **blob store** (D-10) — both must land in the Helm charts / deploy config and CI the
  same portable way (`deploy/helm/veridoc`, `deploy/terraform`).
- Abstraction-behind-interface pattern (KMS in `veridoc-crypto/kms.py`) is the model
  for `OcrEngine` and the blob-store client.

### Integration Points
- The `veridoc-fhir` model lib is the contract the agent fleet (Phases 4–6) reads from;
  keep it clean and independently cloneable.
- Provenance + OCR confidence on FHIR resources feed ALCOA-01 legibility scoring
  (Phase 5) and SDV matching (Phase 5) — the deterministic pseudonym tokens are what
  let SDV later match EMR ↔ Rave for the same patient.
- Redis (Phase 1 sessions) is reused as the ingestion job queue backend (D-06).

</code_context>

<deferred>
## Deferred Ideas

- **LLM-based clinical-entity extraction** from scanned/PDF documents — the extraction
  interface is defined now (D-09) but LLM-backed extraction waits for the Phase 4 LLM
  engine integration; this phase ships rule-based extraction.
- **Proprietary-API adapter implementation** — interface-only this milestone (D-11);
  real implementation waits for an actual proprietary contract to test against.
- **Higher-accuracy / cloud OCR** (docTR, PaddleOCR, Textract, Azure Document
  Intelligence) — swappable behind the `OcrEngine` abstraction (D-07) once
  DEC-cloud-provider is resolved or accuracy demands it.
- **ALCOA+ legibility *scoring agent*** — this phase only emits OCR confidence + flags;
  the agent that assesses all 9 ALCOA+ principles is ALCOA-01 (Phase 5).

</deferred>

---

*Phase: 02-fhir-r4-model-emr-ingestion*
*Context gathered: 2026-06-11*
