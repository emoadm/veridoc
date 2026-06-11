---
phase: 02-fhir-r4-model-emr-ingestion
verified: 2026-06-12T00:00:00Z
status: human_needed
score: 26/26 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Confirm VERIDOC_SITE_MODALITIES config is documented and required in deployment notes"
    expected: "Operators know to populate the JSON map (e.g. {\"site-001\":\"hl7v2\"}) before deploying; an unregistered site returns HTTP 400 by design"
    why_human: "CR-04 modality routing was fixed by making unregistered sites fail closed (HTTP 400). The config key is present in config.py and values.yaml. A human must confirm this is surfaced in operator onboarding docs (or an explicit note in the service README) so no site is accidentally left unregistered in a real deployment."
---

# Phase 2: FHIR R4 Model + EMR Ingestion — Verification Report

**Phase Goal:** Canonical FHIR R4 patient model and ingestion framework (synthetic FHIR, HL7 v2.x, semi-manual import, OCR).
**Verified:** 2026-06-12
**Status:** human_needed
**Re-verification:** No — initial verification (post code-review fix pass)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All 9 FHIR R4B resource types + Provenance construct, validate, and serialize via the R4B sub-package | VERIFIED | `models.py` imports exclusively from `fhir.resources.R4B.*`; `__all__` gates 10 classes; `test_models.py` 26 tests pass |
| 2 | Synthea bundles + AdverseEvent fixture load into the model and round-trip | VERIFIED | 5 Synthea JSON bundles + `adverse_event.json` exist under `libs/veridoc-fhir/tests/fixtures/fhir/`; `test_models.py` covers load+round-trip |
| 3 | FhirRepository.save() upserts to MongoDB; find_by_patient() returns it | VERIFIED | `repository.py` uses `AsyncMongoClient`, compound unique index `(resourceType,id)`, replace_one upsert; `test_repository.py` passes (skips without Docker) |
| 4 | create_provenance() produces a Provenance with meta.source, ingestion-path, and optional OCR-confidence | VERIFIED | `provenance.py` assigns a stable UUID id (CR-02 fix), sets `meta.source`, always emits `ingestion-path` extension, conditionally emits `ocr-confidence`; `test_provenance.py` 12 tests pass |
| 5 | NativeFhirAdapter loads a Synthea R4B bundle and returns parsed FHIR resources | VERIFIED | `adapters/native_fhir.py` parses, validates via R4B classes, pseudonymizes; `test_adapters.py::test_native_fhir` passes |
| 6 | HL7v2Adapter maps ADT_A01 to Patient + Encounter and ORU_R01 to Observation + DiagnosticReport via hl7apy + explicit mapping layer | VERIFIED | `adapters/hl7v2.py` delegates to `mapping/hl7v2_fhir.py`; `map_adt_a01_to_fhir` / `map_oru_r01_to_fhir` use `parse_message`; both adapter tests pass |
| 7 | PdfExcelAdapter normalizes PDF/Excel to the same FHIR R4B model | VERIFIED | `adapters/pdf_excel.py` uses pypdf/openpyxl + RuleBasedExtractor; `test_adapters.py::test_pdf_excel` passes |
| 8 | OcrAdapter produces a DocumentReference carrying OCR confidence + ALCOA legibility flags and stores the original to blob | VERIFIED | `adapters/ocr.py` builds DocumentReference with `docStatus="preliminary"`, `ocr-confidence` extension, legibility flags at 0.95/0.85; `test_ocr` + `test_ocr_flags` pass; `test_regression_legibility_flags.py` passes |
| 9 | Every adapter pseudonymizes PII via veridoc-pseudonym using the SAME canonical `patient_pseudonym(site_id, natural_id)` namespace; same patient → same token across sources | VERIFIED | All four adapters import and call `patient_pseudonym()`; CR-05 unified the namespace; `test_regression_pseudonym_namespace.py` 6 tests pass |
| 10 | POST /ingest/{site_id} is async, authenticates, is tenancy-scoped fail-closed, deny-by-default RBAC, resolves real modality from SourceProfile, enqueues an RQ job, and returns 202 | VERIFIED | `api/ingest.py` is `async def post_ingest`; `await request.body()` (CR-01 fix); `_resolve_modality()` resolves from `app.state.source_registry` and returns HTTP 400 for unknown site (CR-04 fix); `require_write_role` deny-by-default; `test_ingest_api.py` passes |
| 11 | The enqueue path writes a same-transaction "ingest:enqueued" audit event through veridoc-audit | VERIFIED | `api/ingest.py` calls `append_audit` + `session.commit()` via `run_in_threadpool`; tested in `test_ingest_api.py` |
| 12 | The RQ worker uses get_resource_type() (not resource_type), opens its own session, persists FHIR + Provenance to Mongo, and commits an "ingest:completed" audit event | VERIFIED | `worker.py:164` uses `resource.get_resource_type()` (CR-03 fix); `ingest_job` calls `_session_scope` + `append_audit` + `session.commit()`; `test_regression_worker_ingest.py` 2 tests pass |
| 13 | SourceAdapter ABC + SourceModality enum + SourceProfileRegistry define the ingestion contract | VERIFIED | `adapter.py` has `SourceModality` StrEnum with 5 values (NATIVE_FHIR, HL7V2, PDF_EXCEL, OCR, PROPRIETARY); `registry.py` maps all 5 modalities to adapter classes |
| 14 | OcrEngine ABC with TesseractEngine emits document-level confidence + ALCOA flags; cloud stubs raise NotImplementedError | VERIFIED | `ocr_engine.py` uses `pytesseract.image_to_data`, computes doc_conf as mean of word confs / 100, sets `flagged < 0.95`, `escalated < 0.85`; Textract + Azure stubs raise NotImplementedError |
| 15 | BlobStore ABC with S3BlobStore round-trips bytes via MinIO; AzureBlobStore raises NotImplementedError | VERIFIED | `blob_store.py` uses `boto3` with `endpoint_url` for MinIO; `test_blob_store.py` passes (skips without Docker) |
| 16 | MongoDB Helm template renders as a Deployment with credentials from secretKeyRef (no inlined secrets) | VERIFIED | `templates/mongodb.yaml` uses `secretKeyRef` for `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD`; `values.yaml` has `mongodb` section |
| 17 | MinIO Helm template renders as a Deployment exposing API (9000) + console (9001) with credentials from secretKeyRef | VERIFIED | `templates/minio.yaml` has `--console-address :9001`, `MINIO_ROOT_USER` + `MINIO_ROOT_PASSWORD` via `secretKeyRef` |
| 18 | Helm chart renders ingestion-service API + RQ-worker Deployments with Mongo/Redis/blob env via secretKeyRef | VERIFIED | `templates/ingestion-service.yaml` has two Deployments, worker command pins `rq.serializers.JSONSerializer`, all creds via `secretKeyRef` |
| 19 | CI installs tesseract-ocr and runs the Phase 2 test suites | VERIFIED | `ci.yml` has `sudo apt-get install -y tesseract-ocr tesseract-ocr-eng`; runs `services/ingestion-service/tests/` |
| 20 | CI kind deploy job includes veridoc-mongodb, veridoc-minio, veridoc-ingestion-service in the diagnose loop and a smoke test POSTs to /ingest/{site_id} | VERIFIED | `ci.yml` lists all three in the deploy loop and has an "Ingest smoke test" step |
| 21 | Package legitimacy gate: all 9 Phase 02 packages (incl. Pillow) carry APPROVED verdicts in PACKAGE-LEGITIMACY.md | VERIFIED | `docs/validation/PACKAGE-LEGITIMACY.md` Phase 02 section: all 9 packages APPROVED (2026-06-11) |
| 22 | Both libs (veridoc-fhir, veridoc-ingestion) are registered as uv-workspace members | VERIFIED | `pyproject.toml` lines 26-27: `veridoc-fhir = { workspace = true }` + `veridoc-ingestion = { workspace = true }` |
| 23 | motor is absent from the dependency graph | VERIFIED | `grep "motor" uv.lock` produces no output (excluding comments); `repository.py` explicitly imports `AsyncMongoClient` from `pymongo` |
| 24 | Regression tests (Docker-free) cover CR-02 Provenance KeyError, CR-03 AttributeError, CR-05 pseudonym namespace, IN-01 legibility flags | VERIFIED | All four regression test files exist and pass: `test_regression_save_provenance.py` (2), `test_regression_worker_ingest.py` (2), `test_regression_pseudonym_namespace.py` (6), `test_regression_legibility_flags.py` (1) |
| 25 | Full test suite is green: 87 passed, 20 skipped (Docker/tesseract-gated only) | VERIFIED | `uv run pytest libs/veridoc-fhir libs/veridoc-ingestion services/ingestion-service -q` exits 0; `87 passed, 20 skipped in 2.60s` |
| 26 | HL7 resources carry real `meta.source = urn:veridoc:source:hl7v2:{site_id}` (not hardcoded "site") on Patient, Encounter, Observation, DiagnosticReport | VERIFIED | `hl7v2_fhir.py` defines `_hl7_source_urn(site_id)`, threads `site_id` into both mapping functions, stamps `meta.source` on every emitted resource (CR-06 + WR-07 fixes) |

**Score:** 26/26 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `libs/veridoc-fhir/src/veridoc_fhir/models.py` | R4B-only re-exports of 9 resources + Provenance | VERIFIED | Imports from `fhir.resources.R4B.*`; `__all__` = 10 classes |
| `libs/veridoc-fhir/src/veridoc_fhir/repository.py` | AsyncMongoClient-backed FhirRepository | VERIFIED | `AsyncMongoClient`, unique `(resourceType,id)` index, `replace_one` upsert, CR-02 UUID fallback |
| `libs/veridoc-fhir/src/veridoc_fhir/provenance.py` | `create_provenance()` factory with stable UUID id | VERIFIED | Assigns `str(uuid.uuid4())` id, sets `meta.source`, always emits `ingestion-path` extension |
| `libs/veridoc-fhir/src/veridoc_fhir/extensions.py` | Extension URL constants incl. `urn:veridoc:extension:ocr-confidence` | VERIFIED | All 3 URN constants present and exported |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py` | SourceAdapter ABC + SourceModality StrEnum + SourceProfile dataclass | VERIFIED | All 5 modality values; ABC with abstract `ingest()` |
| `libs/veridoc-ingestion/src/veridoc_ingestion/registry.py` | SourceProfileRegistry with all 5 modalities mapped | VERIFIED | All 4 real adapters + ProprietaryAdapter wired in modality table |
| `libs/veridoc-ingestion/src/veridoc_ingestion/ocr_engine.py` | TesseractEngine + ALCOA thresholds + cloud stubs | VERIFIED | `image_to_data` used; 0.95/0.85 thresholds; NotImplementedError stubs |
| `libs/veridoc-ingestion/src/veridoc_ingestion/blob_store.py` | S3BlobStore with `endpoint_url` + AzureBlobStore stub | VERIFIED | `endpoint_url` conditional for MinIO; AzureBlobStore raises NotImplementedError |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py` | NativeFhirAdapter with pseudonymization | VERIFIED | Uses `patient_pseudonym()`; WR-01 dropped-resource logging |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py` | HL7v2Adapter with exact dispatch + WR-06 dead-letter | VERIFIED | Dispatch on `(msg_code, trigger)` tuple (WR-04); raises ValueError on empty PID.3 (WR-06) |
| `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py` | `map_adt_a01_to_fhir` + `map_oru_r01_to_fhir` with real `meta.source` | VERIFIED | `_hl7_source_urn(site_id)` applied to every resource (CR-06 + WR-07); DTM parsed by explicit lengths (WR-05) |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/pdf_excel.py` | PdfExcelAdapter with pypdf/openpyxl + pseudonymization | VERIFIED | Uses `patient_pseudonym()`; WR-01 dropped-resource logging |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/ocr.py` | OcrAdapter with DocumentReference, legibility flags, blob retention | VERIFIED | `docStatus="preliminary"`, `ocr-confidence` extension, legibility flags at 0.95/0.85, `patient_pseudonym()` |
| `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py` | `ingest_job` with `get_resource_type()`, `try/finally` close, own audit commit | VERIFIED | CR-03 fixed; WR-02 `try/finally: repo.close()`; WR-03 no fallback; `append_audit` + `session.commit()` |
| `services/ingestion-service/src/ingestion_service/api/ingest.py` | `async def post_ingest`, `await request.body()`, real modality resolution | VERIFIED | CR-01 + CR-04 fixed; `_resolve_modality()` returns HTTP 400 for unknown site |
| `services/ingestion-service/src/ingestion_service/main.py` | FastAPI lifespan with `create_indexes()` + JSONSerializer | VERIFIED | Both present; `site_modalities` config populates `source_registry` at startup |
| `services/ingestion-service/Dockerfile` | tesseract-ocr in builder + runtime stages | VERIFIED | Lines 31-32 (builder) and 62-63 (runtime) |
| `deploy/helm/veridoc/templates/mongodb.yaml` | MongoDB Deployment with secretKeyRef credentials | VERIFIED | `MONGO_INITDB_ROOT_*` via `secretKeyRef` |
| `deploy/helm/veridoc/templates/minio.yaml` | MinIO Deployment, ports 9000 + 9001, secretKeyRef | VERIFIED | `--console-address :9001`; `MINIO_ROOT_*` via `secretKeyRef` |
| `deploy/helm/veridoc/templates/ingestion-service.yaml` | API + RQ-worker Deployments with JSONSerializer + secretKeyRef | VERIFIED | Two Deployments; worker command pins `rq.serializers.JSONSerializer`; all creds via `secretKeyRef` |
| `.github/workflows/ci.yml` | tesseract install + Phase 2 suites + kind smoke test | VERIFIED | `tesseract-ocr-eng` installed; `test_ingest_api.py` run; smoke test step present |
| `docs/validation/PACKAGE-LEGITIMACY.md` | Phase 02 section with 9 APPROVED verdicts | VERIFIED | All 9 packages APPROVED (2026-06-11) |
| `libs/veridoc-fhir/tests/fixtures/fhir/adverse_event.json` | Hand-crafted R4B AdverseEvent fixture | VERIFIED | File exists |
| `libs/veridoc-ingestion/tests/fixtures/hl7/adt_a01.hl7` | HL7 ADT_A01 fixture | VERIFIED | File exists |
| `libs/veridoc-ingestion/tests/fixtures/images/scan_legible.png` | Legible image fixture | VERIFIED | File exists |
| `libs/veridoc-fhir/tests/conftest.py` | MongoDbContainer session fixture | VERIFIED | `MongoDbContainer("mongo:7-jammy")` + `mongo_url` fixture present |
| `libs/veridoc-ingestion/tests/conftest.py` | MinioContainer session fixture | VERIFIED | `MinioContainer` + `minio_endpoint` fixture present |
| `scripts/gen_synthea_fixtures.sh` | Reproducible Synthea generation with `-s 42 --use_us_core_ig=false` | VERIFIED | File exists; both flags present (5 occurrences confirmed) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `api/ingest.py` | Redis (RQ ingestion queue) | `queue.enqueue(ingest_job, ...)` with JSON-serializable args | VERIFIED | `enqueue` call present; all args are primitives |
| `worker.py` | `veridoc_audit.append_audit` | `_session_scope` + `append_audit` + `session.commit()` | VERIFIED | D-06 deviation explicit in code and docs |
| `adapters/*.py` | `veridoc_pseudonym.patient_pseudonym` | `patient_pseudonym(site_id, natural_id)` in all four adapters | VERIFIED | CR-05 fix confirmed; all four adapters use canonical helper |
| `hl7v2.py` | `mapping/hl7v2_fhir.py` | `hl7v2_fhir.map_adt_a01_to_fhir` / `map_oru_r01_to_fhir` | VERIFIED | Adapter delegates segment mapping to the explicit mapping layer (D-12) |
| `repository.py` | MongoDB `fhir_resources` collection | `AsyncMongoClient.replace_one` upsert + compound indexes | VERIFIED | `create_index` calls present; `replace_one(upsert=True)` used |
| `templates/mongodb.yaml` | `templates/secrets.yaml` | `secretKeyRef` on MongoDB credentials | VERIFIED | Both `MONGO_INITDB_ROOT_*` via `secretKeyRef` |
| `templates/minio.yaml` | `templates/secrets.yaml` | `secretKeyRef` on MinIO credentials | VERIFIED | Both `MINIO_ROOT_*` via `secretKeyRef` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `api/ingest.py` | `payload_bytes` | `await request.body()` | Yes — from HTTP request | FLOWING |
| `worker.py` | `resources` | `adapter.ingest(payload_bytes, profile)` | Yes — real adapter execution | FLOWING |
| `worker.py` | `provenance` | `create_provenance(target_ref, source, ...)` | Yes — live Provenance factory | FLOWING |
| `api/ingest.py` | `modality` | `_resolve_modality(request, site_id)` from `app.state.source_registry` | Yes — from site config | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite 87 passed / 20 skipped | `uv run pytest libs/veridoc-fhir libs/veridoc-ingestion services/ingestion-service -q` | `87 passed, 20 skipped in 2.60s`; exit 0 | PASS |
| worker.py uses `get_resource_type()` not `resource_type` | `grep "get_resource_type" worker.py` | Line 164: `if resource.get_resource_type() == "Patient"` | PASS |
| ingest.py is `async def` and uses `await request.body()` | `grep "async def\|await request.body" ingest.py` | Both present at lines 116 + 150 | PASS |
| All four adapters use canonical `patient_pseudonym` | `grep -l "patient_pseudonym" adapters/*.py` | All four adapter files confirmed | PASS |
| No motor in repository.py or uv.lock | `grep "motor" repository.py uv.lock` (excl. comments) | No matches | PASS |
| workspace members registered | `grep "veridoc-fhir\|veridoc-ingestion" pyproject.toml` | Both lines 26-27 | PASS |

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` probes were declared or found. The test suite is the phase's primary automated verification mechanism. Tests run above confirmed 87 passed / 20 skipped.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EMR-01 | 02-01 through 02-07 | FHIR R4 canonical model + heterogeneous ingestion (native FHIR, HL7 v2.x, PDF/Excel, OCR) + pseudonymization + provenance | SATISFIED | 9 R4B resource types + Provenance; 4 working adapters; `patient_pseudonym` across all adapters; `create_provenance`; service + worker + Helm chart + CI |

EMR-01 is the sole requirement mapped to Phase 2 in REQUIREMENTS.md. All sub-bullets are addressed:
- 9 R4B resource types: VERIFIED (models.py)
- Per-site source modality as first-class configurable property: VERIFIED (`VERIDOC_SITE_MODALITIES` config + SourceProfileRegistry populated at startup)
- Native FHIR adapter: VERIFIED (NativeFhirAdapter)
- HL7 v2.x adapter: VERIFIED (HL7v2Adapter + hl7v2_fhir mapping)
- Proprietary-API adapter stub: VERIFIED (ProprietaryAdapter raises NotImplementedError — D-11)
- Semi-manual import (PDF/Excel): VERIFIED (PdfExcelAdapter)
- OCR path with ALCOA confidence flags: VERIFIED (OcrAdapter + TesseractEngine)
- Provenance with source modality + OCR confidence: VERIFIED (create_provenance)
- Pseudonymization at ingestion: VERIFIED (patient_pseudonym across all adapters)

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py` | 196 | `except Exception: continue` (validation failures) | Info | WR-01 was fixed — this block now logs the drop before continuing. Not a silent stub; clinical-data loss is auditable |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/pdf_excel.py` | 200 | Same `except Exception: continue` pattern | Info | Same WR-01 fix applied; logged with site_id + error |

No TBD / FIXME / XXX markers found in any Phase 2 modified file. No `return null` / `return []` stubs. No hardcoded placeholder patterns. The `NotImplementedError` raises in ProprietaryAdapter, cloud OCR stubs, and AzureBlobStore are intentional interface stubs with `# pragma: no cover` annotations — correct per the kms.py analog pattern.

### Human Verification Required

**1. VERIDOC_SITE_MODALITIES operator config (CR-04 modality routing)**

**Test:** In a deployment guide or service README, confirm that operators are instructed to set `VERIDOC_SITE_MODALITIES` to a JSON map of site IDs to modality slugs before going live (e.g. `{"site-001": "hl7v2", "site-002": "native-fhir"}`).

**Expected:** An unregistered site returns HTTP 400 by design (fail-closed behavior is correct and tested). However, if operators are unaware of the config requirement, every site will return 400 until configured — which could look like a service outage. The config key exists in `config.py` and `values.yaml`, but a human must verify there is a clear operator note in the deployment docs so this is not a surprise in production.

**Why human:** The code is correct and tested. This is an operational documentation / onboarding gap that cannot be verified programmatically. If a deployment README/operator guide already documents this, the item is resolved.

---

## Gaps Summary

No gaps. All 26 must-haves are VERIFIED. The three independent crashes identified in 02-REVIEW.md (CR-01 RuntimeError, CR-02 KeyError, CR-03 AttributeError) are confirmed fixed in code. The pseudonym namespace (CR-05), hardcoded meta.source (CR-06), and all 8 warnings are fixed. The regression test suite (87 passed / 20 skipped; 20 skips are all Docker/tesseract-gated) confirms no regressions.

The single human-verification item (CR-04 operator config documentation) is a deployment-readiness concern, not a code correctness gap. It does not block phase goal achievement.

---

_Verified: 2026-06-12_
_Verifier: Claude (gsd-verifier)_
