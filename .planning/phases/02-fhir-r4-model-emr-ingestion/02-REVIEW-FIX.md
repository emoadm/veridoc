---
phase: 02-fhir-r4-model-emr-ingestion
fixed_at: 2026-06-12
review_path: .planning/phases/02-fhir-r4-model-emr-ingestion/02-REVIEW.md
iteration: 1
findings_in_scope: 18
fixed: 16
skipped: 2
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-06-12
**Source review:** 02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 18 (6 critical/blocker, 8 warning, 4 info)
- Fixed: 16 (all 6 critical, all 8 warning, IN-01, IN-03)
- Deferred / no-action: 2 (IN-02 perf out-of-scope, IN-04 no change required)
- Final test result: `87 passed, 20 skipped` (Docker/MinIO/Postgres/tesseract gated only).
  No AttributeError / KeyError / RuntimeError. Up from 76 passed before the fixes.

The three independent crashes the reviewer reproduced (CR-01 RuntimeError, CR-02
KeyError, CR-03 AttributeError) are now exercised in-process by new Docker-free
regression tests that drive the real fhir.resources runtime API and the worker
persistence path — the exact gaps that let the originals ship green.

## Fixed Issues

### CR-01 + CR-04: async ingest handler + real per-site modality routing
**Files modified:** `services/ingestion-service/src/ingestion_service/api/ingest.py`,
`services/ingestion-service/src/ingestion_service/main.py`,
`services/ingestion-service/src/ingestion_service/config.py`,
`services/ingestion-service/tests/test_ingest_api.py`
**Commit:** 2091448
**Applied fix:** `post_ingest` is now `async def` and reads `await request.body()`.
Removed the `request.scope.get("_body")` read and the
`asyncio.get_event_loop().run_until_complete()` hack entirely. The blocking blob
`put`, RQ `enqueue`, and the audit-write + `session.commit()` are offloaded via
`fastapi.concurrency.run_in_threadpool` so they never block the event loop. RBAC
(deny-by-default), fail-closed tenancy, and the same-transaction `ingest:enqueued`
audit event are preserved. CR-04: the handler resolves the REAL modality from the
site's registered `SourceProfile` (new `site_modalities` config → `SourceProfileRegistry`
populated at startup) instead of hardcoding `"native-fhir"`; an unregistered site
fails closed (HTTP 400). Test fixtures register `site-001` as native-fhir.

### CR-02: persist resources without a populated id (every Provenance)
**Files modified:** `libs/veridoc-fhir/src/veridoc_fhir/repository.py`,
`libs/veridoc-fhir/src/veridoc_fhir/provenance.py`
**Commit:** 0831404
**Applied fix:** `create_provenance` now assigns a stable UUID `id` so the Provenance
is addressable. `FhirRepository.save()` also defaults a UUID `id` when `model_dump()`
omits it (fhir.resources drops a `None` id) and keys the idempotent upsert on
`(resourceType, id)` — no more `KeyError: 'id'` aborting the job after clinical
resources were persisted but before Provenance.

### CR-03: use get_resource_type() instead of nonexistent resource_type
**Files modified:** `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py`
**Commit:** 8248654
**Applied fix:** Replaced `resource.resource_type` with the classmethod
`resource.get_resource_type()` (verified against the installed fhir.resources R4B
runtime). The per-resource loop no longer raises AttributeError on the first resource.

### CR-05: unify the pseudonym key-namespace across all adapters
**Files modified:** `libs/veridoc-pseudonym/src/veridoc_pseudonym/pseudonym.py`,
`libs/veridoc-pseudonym/src/veridoc_pseudonym/__init__.py`,
`libs/veridoc-ingestion/src/veridoc_ingestion/adapters/{native_fhir,hl7v2,pdf_excel,ocr}.py`
**Commit:** ba1845d
**Applied fix:** Added the single canonical helpers `patient_key_namespace(site_id,
natural_id) == f"{site}-{natural}"` and `patient_pseudonym(site_id, natural_id)` to
veridoc-pseudonym. Confirmed from the `pseudonym_token` contract that the FIRST
argument selects the *per-patient* crypto key, so the namespace must be per-patient
(`site-natural`), never per-site. All four adapters now route through
`patient_pseudonym`, so the same physical patient yields ONE token across modalities
(SC-4) and per-patient crypto-shredding works (D-14). Previously hl7v2/pdf_excel/ocr
keyed on `site_id` alone, collapsing all patients at a site onto one key.

### CR-06 + WR-04 + WR-07: real HL7 meta.source on every resource + exact dispatch
**Files modified:** `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py`,
`libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py`
**Commit:** 9b836c5
**Applied fix:** Threaded `site_id` into `map_adt_a01_to_fhir` / `map_oru_r01_to_fhir`
and set `meta.source = urn:veridoc:source:hl7v2:{site_id}` on EVERY emitted resource —
Patient (CR-06, was the literal `"site"`), and Encounter/Observation/DiagnosticReport
(WR-07, previously had no source). WR-04: HL7 message-type dispatch now keys on the
parsed `(MSH-9 msg_1, msg_2)` tuple rather than a substring `in` test. Verified all
emitted resources carry the real site URN.

### WR-01: log dropped resources instead of silently swallowing
**Files modified:** `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py`,
`libs/veridoc-ingestion/src/veridoc_ingestion/adapters/pdf_excel.py`
**Commit:** f6612c7
**Applied fix:** Both adapters now log each resource dropped on R4B validation failure
(resourceType + error + site_id) and emit a per-batch dropped-count summary, making
clinical-data loss visible/auditable rather than silent.

### WR-02 + WR-03: close Mongo client in finally + fail closed on unknown modality
**Files modified:** `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py`
**Commit:** 0a62de2
**Applied fix:** WR-02 — repo usage is wrapped in `try/finally: repo.close()`, so the
AsyncMongoClient is always closed even on a mid-batch exception (was leaked).
WR-03 — removed the `except ValueError: mod = NATIVE_FHIR` fallback; an unrecognized
modality now raises and the RQ job is dead-lettered rather than running the wrong
parser on PHI bytes.

### WR-05: parse HL7 DTM by explicit lengths and honor timezone offset
**Files modified:** `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py`
**Commit:** c728f97
**Applied fix:** `_parse_hl7_datetime` slices by known field lengths (14/12/8) instead
of the fragile `len(fmt.replace("%","XX"))` heuristic, and honors an explicit
`+/-HHMM` offset present in the DTM instead of forcing UTC on local facility times.

### WR-06: reject missing/empty PID.3 instead of merging under an "UNKNOWN" sentinel
**Files modified:** `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py`
**Commit:** 6d5c4bb
**Applied fix:** `_extract_natural_id` now raises `ValueError` (dead-letters the
message) when the PID segment is absent or PID.3 is empty, instead of returning the
literal `"UNKNOWN"` that HMAC'd every MRN-less message into one shared pseudonym and
silently merged distinct patients' clinical data.

### WR-08: drop the redundant non-unique standalone id index
**Files modified:** `libs/veridoc-fhir/src/veridoc_fhir/repository.py`
**Commit:** df99f81
**Applied fix:** Removed the unused single-field `id` index (no query path uses a bare
id; it implied a global-id-uniqueness contract this single-collection design does not
make — identity is the `(resourceType, id)` tuple) and documented the index contract.
The unique compound `(resourceType, id)` index is unchanged.

### IN-01: assert both ALCOA legibility-flag instances coexist
**Files modified:** `libs/veridoc-ingestion/tests/test_regression_legibility_flags.py`
**Commit:** 2904ff9
**Applied fix:** Added a regression test asserting that below confidence 0.85 a
DocumentReference carries both `legibility-flag` and `legibility-escalate` extension
instances under the same URL (the reviewer's suggested coverage). No source change.

### IN-03: word-boundary analyte matching in RuleBasedExtractor
**Files modified:** `libs/veridoc-ingestion/src/veridoc_ingestion/extraction.py`
**Commit:** 9cc8554
**Applied fix:** Replaced bare substring containment (`keyword in name_raw`) with
word-boundary regex matching so a future analyte name embedding another keyword can
no longer be mis-keyed to the wrong LOINC as the table grows.

### Regression tests (would have caught CR-02 / CR-03 / CR-05)
**Files added:**
`libs/veridoc-fhir/tests/test_regression_save_provenance.py`,
`libs/veridoc-ingestion/tests/test_regression_worker_ingest.py`,
`libs/veridoc-ingestion/tests/test_regression_pseudonym_namespace.py`,
`libs/veridoc-ingestion/tests/test_regression_legibility_flags.py`
**Commit:** 2904ff9
**Applied fix:** In-process (NO Docker) tests that:
- round-trip a `create_provenance` Provenance through `FhirRepository.save` via an
  in-memory async collection double, asserting no KeyError and a well-formed upsert
  filter (CR-02);
- run `worker._async_ingest` over a REAL Synthea fixture bundle with fakes for blob /
  repo, asserting it reaches persistence with no AttributeError/KeyError, persists a
  Patient + Provenance (>1 resource), closes the repo (WR-02), and fails closed on an
  unknown modality (WR-03) (CR-02/CR-03);
- assert all four adapters use the single canonical pseudonym namespace and the OCR
  adapter emits exactly `patient_pseudonym(site, natural_id)` (CR-05/SC-4).

## Skipped / Deferred Issues

### IN-02: find_by_patient(length=None) loads the full result set into memory
**File:** `libs/veridoc-fhir/src/veridoc_fhir/repository.py:143-147`
**Reason:** Deferred — performance concern the reviewer explicitly logged as
out-of-v1-scope info-only. No correctness or security impact; pagination is a
forward-looking enhancement best done when a caller needs it.

### IN-04: audit `after` payloads embed `payload_key`
**File:** `services/ingestion-service/src/ingestion_service/api/ingest.py:173-177`,
`libs/veridoc-ingestion/src/veridoc_ingestion/worker.py:281-287`
**Reason:** No action required — the reviewer marked this "None required". The blob key
scheme is already PHI-free (`{site_id}/{uuid}.bin`); the finding only flags that it
should stay that way. No code change.

---

_Fixed: 2026-06-12_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
