---
phase: 02-fhir-r4-model-emr-ingestion
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 45
files_reviewed_list:
  - libs/veridoc-fhir/pyproject.toml
  - libs/veridoc-fhir/src/veridoc_fhir/extensions.py
  - libs/veridoc-fhir/src/veridoc_fhir/__init__.py
  - libs/veridoc-fhir/src/veridoc_fhir/models.py
  - libs/veridoc-fhir/src/veridoc_fhir/provenance.py
  - libs/veridoc-fhir/src/veridoc_fhir/repository.py
  - libs/veridoc-fhir/tests/conftest.py
  - libs/veridoc-fhir/tests/test_models.py
  - libs/veridoc-fhir/tests/test_provenance.py
  - libs/veridoc-fhir/tests/test_repository.py
  - libs/veridoc-ingestion/pyproject.toml
  - libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/__init__.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/ocr.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/pdf_excel.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/proprietary.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/blob_store.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/extraction.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/__init__.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/mapping/__init__.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/ocr_engine.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/registry.py
  - libs/veridoc-ingestion/src/veridoc_ingestion/worker.py
  - libs/veridoc-ingestion/tests/conftest.py
  - libs/veridoc-ingestion/tests/test_adapters.py
  - libs/veridoc-ingestion/tests/test_blob_store.py
  - libs/veridoc-ingestion/tests/test_ocr_engine.py
  - libs/veridoc-ingestion/tests/test_registry.py
  - services/ingestion-service/Dockerfile
  - services/ingestion-service/pyproject.toml
  - services/ingestion-service/src/ingestion_service/api/auth_audit.py
  - services/ingestion-service/src/ingestion_service/api/ingest.py
  - services/ingestion-service/src/ingestion_service/api/__init__.py
  - services/ingestion-service/src/ingestion_service/config.py
  - services/ingestion-service/src/ingestion_service/db.py
  - services/ingestion-service/src/ingestion_service/__init__.py
  - services/ingestion-service/src/ingestion_service/main.py
  - services/ingestion-service/src/ingestion_service/worker_main.py
  - services/ingestion-service/tests/conftest.py
  - services/ingestion-service/tests/test_ingest_api.py
  - services/ingestion-service/tests/test_worker_integration.py
  - deploy/helm/veridoc/templates/mongodb.yaml
  - deploy/helm/veridoc/templates/minio.yaml
  - deploy/helm/veridoc/templates/ingestion-service.yaml
  - .github/workflows/ci.yml
  - scripts/gen_synthea_fixtures.sh
findings:
  critical: 6
  blocker: 6
  warning: 8
  info: 4
  total: 18
status: resolved
resolution:
  resolved_at: 2026-06-12
  fixed: [CR-01, CR-02, CR-03, CR-04, CR-05, CR-06, WR-01, WR-02, WR-03, WR-04, WR-05, WR-06, WR-07, WR-08, IN-01, IN-03]
  deferred:
    - id: IN-02
      reason: "find_by_patient pagination is a performance concern the reviewer explicitly logged out of v1 scope; no correctness impact."
    - id: IN-04
      reason: "Reviewer marked 'None required'; blob key scheme is already PHI-free (UUID-based). No code change needed."
  test_result: "87 passed, 20 skipped (Docker/tesseract-gated only); no AttributeError/KeyError/RuntimeError."
---

# Phase 2: Code Review Report

**Reviewed:** 2026-06-11
**Depth:** standard
**Files Reviewed:** 45
**Status:** resolved (fixed 2026-06-12 — see 02-REVIEW-FIX.md)

## Summary

This phase delivers the FHIR R4B model layer (`veridoc-fhir`), the EMR ingestion
adapter stack (`veridoc-ingestion`), and the async `ingestion-service`. The library
boundaries (R4B import discipline, AsyncMongoClient, JSONSerializer-only RQ queue, blob
abstraction, OCR engine, deny-by-default RBAC, fail-closed tenancy, secrets-from-Secrets
in Helm) are structurally sound and many threat mitigations are correctly placed.

However, the **end-to-end ingest path does not work and crashes at three independent
points**, every one of which I reproduced empirically against the installed libraries:

1. The `/ingest/{site_id}` HTTP handler throws `RuntimeError` on **any non-empty body**
   (the common case), so no real document can ever be ingested.
2. `FhirRepository.save()` throws `KeyError: 'id'` when persisting the Provenance
   resource produced by `create_provenance` (it has no `id`), aborting every worker job.
3. The worker references `resource.resource_type`, an attribute that does not exist on
   `fhir.resources` models (`AttributeError`), aborting every worker job before Provenance.

On top of those, the pseudonymization key-namespace is **inconsistent across adapters**,
which breaks both cross-source patient matching (SC-4) and per-patient crypto-shredding
(D-14) for the HL7v2 and PDF/Excel paths, and the API **hardcodes `modality="native-fhir"`**
so HL7/PDF/OCR sites are silently routed to the wrong adapter.

Severity tiers below use `critical`/`blocker` interchangeably per the canonical schema;
all six are ship-blocking.

## Critical Issues

### [RESOLVED] CR-01: `/ingest` handler crashes with RuntimeError on any non-empty request body

**File:** `services/ingestion-service/src/ingestion_service/api/ingest.py:112-116`
**Issue:** The handler is a **sync** `def` (runs in an AnyIO worker thread). It tries to
read the body two ways, both broken:
- Line 112 reads `request.scope.get("_body", b"")`. Starlette caches the body as the
  attribute `request._body`, never in `request.scope`, so this always returns `b""`.
- Line 116 then calls `asyncio.get_event_loop().run_until_complete(request.body())`.
  In an AnyIO worker thread there is no current event loop, so `get_event_loop()` raises
  `RuntimeError: There is no current event loop in thread 'AnyIO worker thread'`.

Reproduced: posting `b'{"resourceType":"Bundle"}'` to a sync handler using this exact
code path raises the RuntimeError → HTTP 500. The endpoint can never accept a real
payload; the only reason existing tests might appear green is if they are RED-phase or
the body assertion path is not actually hit. This is the primary deliverable of the phase
and it is non-functional.
**Fix:** Make the handler `async def` and `await request.body()` directly. Sync body
hacks via the event loop are never safe inside FastAPI's threadpool:
```python
@router.post("/{site_id}", response_model=IngestResponse, status_code=202)
async def post_ingest(site_id: str, request: Request,
                      principal: Principal = Depends(require_write_role),
                      session: Session = Depends(get_session)) -> IngestResponse:
    ...
    payload_bytes: bytes = await request.body()
    ...
```
(If the session/append_audit calls must stay synchronous, run them via
`fastapi.concurrency.run_in_threadpool`, but the body read must be awaited.)

### [RESOLVED] CR-02: `FhirRepository.save()` raises KeyError on resources without an `id` (every Provenance)

**File:** `libs/veridoc-fhir/src/veridoc_fhir/repository.py:110-121`
**Issue:** `save()` does `doc = resource.model_dump()` then indexes `doc["id"]` in the
filter. `fhir.resources` omits `id` from `model_dump()` when it is `None`. `create_provenance`
(provenance.py) never sets an `id`, so its dump has no `id` key. Reproduced:
`create_provenance(...).model_dump()` → `'id' not in dump`. The worker calls
`repo.save(provenance)` (worker.py:170) on every job, so `doc["id"]` raises
`KeyError: 'id'` and the ingest job fails after persisting clinical resources but before
recording Provenance — a data-integrity failure (resources stored without their ALCOA/
provenance record).
**Fix:** Default the id and persist it, or skip the id filter when absent:
```python
doc = resource.model_dump()
res_id = doc.get("id")
if res_id is None:
    res_id = str(uuid.uuid4())
    doc["id"] = res_id
result = await self._col.replace_one(
    {"resourceType": doc["resourceType"], "id": res_id}, doc, upsert=True)
return str(result.upserted_id or res_id)
```
Better: have `create_provenance` assign a UUID `id` so Provenance is addressable.

### [RESOLVED] CR-03: Worker uses nonexistent `resource.resource_type` → AttributeError on every job

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py:158-159`
**Issue:** `if resource.resource_type == "Patient"` and `resource.id`. `fhir.resources`
models expose the classmethod `get_resource_type()`, not a `resource_type` attribute.
Reproduced: `Patient(...).resource_type` raises `AttributeError: 'Patient' object has no
attribute 'resource_type'`. The loop runs for every saved resource, so the job aborts as
soon as it processes the first resource (after `repo.save` succeeds but before Provenance).
Combined with CR-02 this means the worker pipeline cannot complete a single ingest.
**Fix:**
```python
if resource.get_resource_type() == "Patient" and patient_id is None:
    patient_id = resource.id or rid
```

### [RESOLVED] CR-04: API hardcodes `modality="native-fhir"` — HL7/PDF/OCR sites routed to the wrong adapter

**File:** `services/ingestion-service/src/ingestion_service/api/ingest.py:147`
**Issue:** The enqueue call always passes `modality="native-fhir"` with a comment claiming
"site registry resolves real modality at worker." It does not: `_async_ingest`
(worker.py:134-142) builds a transient `SourceProfile(site_id, modality=mod, ...)` directly
from the `modality` argument it was given — there is no site-registry lookup of the real
modality anywhere in the worker. Consequently an HL7v2, PDF/Excel, or OCR site will always
run `NativeFhirAdapter.ingest()` on its raw bytes, which then raises `ValueError`
("expected resourceType='Bundle'") for an HL7 message or PDF — so every non-native site
fails, and any that didn't fail would silently mis-ingest. This defeats the entire
multi-modality design (D-11/D-12, SC-2a/SC-2b/SC-3).
**Fix:** Resolve the real modality for `site_id` (from a `SourceProfileRegistry` populated
at startup / from config) in the handler and pass it, or have the worker look up the
profile by `site_id` instead of trusting the passed `modality`.

### [RESOLVED] CR-05: Inconsistent pseudonym key-namespace breaks cross-source matching AND per-patient crypto-shredding

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py:96`,
`adapters/hl7v2.py:112`, `adapters/pdf_excel.py:159`, `adapters/ocr.py:179`
**Issue:** `pseudonym_token(patient_id, natural_id)` derives a *per-patient* key from its
first argument (`get_patient_key(patient_id)`), then HMACs `natural_id`. The adapters pass
the first argument inconsistently:
- native_fhir: `patient_id = f"{site_id}-{raw_patient_id}"` (per-patient namespace)
- hl7v2: `patient_id = profile.site_id` (per-**site** namespace)
- pdf_excel: `patient_id = profile.site_id` (per-**site** namespace)
- ocr: `patient_id = profile.site_id`

Two distinct defects result:
1. **Per-patient crypto-shredding is defeated (D-14) for HL7 and PDF.** All patients at a
   site share the single key `get_patient_key("site-001")`; you cannot erase one patient's
   key without destroying every patient's pseudonym at that site.
2. **Cross-source matching is impossible (SC-4).** The same physical patient arriving via
   native-FHIR (key `site-001-<uuid>`, natural_id `<uuid>`) versus HL7 (key `site-001`,
   natural_id `<MRN>`) produces unrelated tokens — Phase 5 matching cannot link them.
   The docstring in `native_fhir._pseudonymize_patient` explicitly promises "same
   (patient_id, natural_id) → same token across all adapters," which the code violates.
**Fix:** Standardize the key-namespace contract across all adapters (e.g. always
`patient_id = f"{site_id}-{stable_natural_id}"` with `natural_id` the cleaned MRN/UUID),
and document the canonical derivation in one place so all four adapters call it identically.

### [RESOLVED] CR-06: HL7 `Patient.meta.source` hardcoded to a placeholder `site` — loses site provenance

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py:120-122`
**Issue:** `map_adt_a01_to_fhir` sets `"meta": {"source": "urn:veridoc:source:hl7v2:site"}`
— the literal string `site`, not the real `site_id`. The repository indexes
`(resourceType, meta.source)` for provenance source queries (repository.py:89-92), and the
Provenance/audit story depends on `meta.source` identifying the originating site. Every
HL7-ingested Patient is therefore stamped with the same bogus source URN, breaking
source-attribution queries and ALCOA "Attributable" for the HL7 path. (ORU path does not
set `meta.source` at all on its resources — same attribution gap.)
**Fix:** Thread `site_id` (or the full source URN) into the mapping functions and emit
`f"urn:veridoc:source:hl7v2:{site_id}"`, matching the pattern the OCR and PDF adapters
already use.

## Warnings

### [RESOLVED] WR-01: NativeFhirAdapter silently drops any resource that fails R4B validation

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py:186-191`
**Issue:** The `except Exception: continue` swallows *all* validation errors for non-Patient
resources, so a Synthea bundle whose Encounter/Observation carries a US-Core extension (or
any field R4B rejects) is dropped with no log, no metric, no audit. In a clinical-data
pipeline silent data loss is a correctness hazard — a study could be missing observations
and nobody would know. The same pattern appears in `pdf_excel.py:194-196`.
**Fix:** At minimum log the dropped resourceType + validation error and increment a
"dropped_resource" counter; consider failing the batch or routing the bundle to a
dead-letter path so loss is visible.

### [RESOLVED] WR-02: Worker's `asyncio.run` creates a fresh AsyncMongoClient per job and per call

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py:148-178`
**Issue:** Each job builds a new `FhirRepository` (new `AsyncMongoClient`) and calls
`create_indexes()` on every job. `create_indexes` is idempotent but issues four
`create_index` round-trips per job; more importantly a new client + event loop per
`asyncio.run` per job is a connection-churn / resource-leak risk under load (clients are
closed via `repo.close()` only on the success path — an exception between line 148 and 178
leaks the client because there is no `try/finally`).
**Fix:** Wrap repo usage in `try/finally: repo.close()`, and move index creation to worker
startup rather than per-job.

### [RESOLVED] WR-03: `_async_ingest` swallows unknown modality and falls back to native FHIR

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py:134-137`
**Issue:** `except ValueError: mod = SourceModality.NATIVE_FHIR` turns an
unrecognized/garbage modality string into a native-FHIR run instead of failing. Combined
with CR-04 this masks routing bugs and could run the wrong parser on PHI bytes. Fail
closed: an unknown modality should raise and dead-letter the job, not default-route it.
**Fix:** Remove the fallback; let the `ValueError` propagate (RQ will mark the job failed)
or raise a clear domain error.

### [RESOLVED] WR-04: HL7 message-type detection can misroute via substring match

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py:115-118`
**Issue:** Dispatch uses `"ADT^A01" in msg_type` / `"ORU^R01" in msg_type` as a fallback.
`msg_type` is the raw MSH-9 value; a substring test will also match unintended composite
types and is order-sensitive (ADT checked first). Structured field access is available
(`msh_9.msg_1`/`msg_2`/`msg_3`) and should be the authoritative discriminator, not `in`.
**Fix:** Decide solely on the parsed `(msg_code, trigger)` tuple
(`msg_1`,`msg_2`) and the structure (`msg_3`); drop the substring fallback.

### [RESOLVED] WR-05: HL7 datetime parser truncates by a fragile format-length heuristic

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py:66-73`
**Issue:** `value[:len(fmt.replace("%", "XX"))]` computes the slice length by string
substitution on the format. `"%Y%m%d%H%M%S".replace("%","XX")` = `"XXYXXmXXdXXHXXMXXS"`
(length 18), but the actual datetime is 14 chars — so the slice length is wrong for every
format and only works because `strptime` tolerates the over-long slice for the first format
that happens to match. This is brittle and will silently misparse HL7 timezone-suffixed DTM
values (`YYYYMMDDHHMMSS+ZZZZ`). It also assumes UTC for what are local facility times,
which can shift admission timestamps by hours (ALCOA "Contemporaneous").
**Fix:** Parse with explicit known lengths (`value[:14]`, `value[:12]`, `value[:8]`) and
honor any `+/-ZZZZ` offset present in the DTM rather than forcing UTC.

### [RESOLVED] WR-06: `_extract_natural_id` returns the literal `"UNKNOWN"` token, collapsing distinct patients

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py:48-57`
**Issue:** When PID is missing or PID.3 is empty, the function returns `"UNKNOWN"`. That
string is then HMAC'd into the pseudonym token, so *every* HL7 message lacking a usable
MRN maps to the *same* pseudonymized patient at the site — silently merging unrelated
patients' clinical data into one record. For a clinical platform this is a patient-safety/
data-integrity hazard, not a cosmetic default.
**Fix:** Treat a missing/empty PID.3 as a hard error (raise `ValueError`) so the message is
dead-lettered for manual handling rather than merged under a shared sentinel identity.

### [RESOLVED] WR-07: Provenance/`meta.source` not set on Encounter/Observation/DiagnosticReport in HL7 mapping

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py:145-156, 232-272`
**Issue:** Only Patient gets a `meta.source` (and that one is the CR-06 placeholder). The
Encounter, Observation, and DiagnosticReport resources produced from HL7 carry no
`meta.source`, so the `(resourceType, meta.source)` index and source-attribution queries
return nothing for them. ALCOA "Attributable" requires every persisted resource to carry
its origin.
**Fix:** Set `meta.source = f"urn:veridoc:source:hl7v2:{site_id}"` on every resource the
mapping emits.

### [RESOLVED] WR-08: Single-field `id` index is non-unique and overlaps the unique compound index

**File:** `libs/veridoc-fhir/src/veridoc_fhir/repository.py:80-93`
**Issue:** `create_indexes` builds a unique `(resourceType, id)` index plus a separate
non-unique single-field `id` index. Because `find_by_patient` never queries by bare `id`
and `save` filters on `(resourceType, id)`, the standalone `id` index is unused write
overhead today, and—more importantly—an `id` collision across resource types is *not*
prevented (two resources with the same `id` but different `resourceType` coexist). If any
caller ever looks up "the resource with id X" expecting uniqueness, it will get multiple
docs. Confirm whether global-id uniqueness is intended; if so the index is wrong, if not
the standalone `id` index should be dropped.
**Fix:** Either make global `id` uniqueness explicit (and the matching index unique) or
remove the redundant `id` index; document the chosen contract.

## Info

### [RESOLVED] IN-01: `extensions.py`/`__init__` export `ALCOA_LEGIBILITY_FLAG_URL` but provenance/repository ignore it

**File:** `libs/veridoc-fhir/src/veridoc_fhir/extensions.py:38-39`
**Issue:** The constant is exported and only used by the OCR adapter. Fine for now, but the
docstring claims "Multiple instances may appear on a single DocumentReference" — the OCR
adapter does emit two flags below 0.85, so the data model is consistent; just noting the
constant has a single consumer.
**Fix:** None required; consider a unit test asserting both flag instances coexist in the
serialized DocumentReference.

### [DEFERRED] IN-02: `find_by_patient(length=None)` loads the full result set into memory

**File:** `libs/veridoc-fhir/src/veridoc_fhir/repository.py:143-147`
**Issue:** `cursor.to_list(length=None)` materializes every matching document. For a patient
with a large observation history this is unbounded memory. (Performance is out of v1 scope,
logged as info only.)
**Fix:** Accept an optional limit / expose pagination when callers need it.

### [RESOLVED] IN-03: `RuleBasedExtractor` regex can mis-key analytes via substring containment

**File:** `libs/veridoc-ingestion/src/veridoc_ingestion/extraction.py:120-123`
**Issue:** `if keyword in name_raw` matches substrings, so a future analyte name containing
another keyword (e.g. a hypothetical "Sodium-adjusted X") could map to the wrong LOINC. With
the current 11-entry table there is no collision, but the containment check is a latent
correctness trap as the table grows.
**Fix:** Prefer exact/word-boundary matching against the cleaned analyte name.

### [NO ACTION] IN-04: `ingest:enqueued` and worker `ingest:completed` audit `after` payloads embed `payload_key`

**File:** `services/ingestion-service/src/ingestion_service/api/ingest.py:173-177`,
`libs/veridoc-ingestion/src/veridoc_ingestion/worker.py:281-287`
**Issue:** The audit rows store `payload_key` / `entity_id=payload_key`. The key is
`{site_id}/{uuid}.bin` and contains no PHI, so this is acceptable; flagging only to confirm
the key scheme stays PHI-free (do not start embedding MRNs or filenames into the key).
**Fix:** None required; keep blob keys opaque (UUID-based) as currently done.

---

_Reviewed: 2026-06-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
