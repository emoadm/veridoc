---
phase: 02-fhir-r4-model-emr-ingestion
plan: "03"
subsystem: veridoc-fhir
tags: [fhir, r4b, mongodb, provenance, repository, models]
dependency_graph:
  requires: ["02-01"]
  provides: ["veridoc_fhir.models", "veridoc_fhir.repository", "veridoc_fhir.provenance", "veridoc_fhir.extensions"]
  affects: ["02-05", "02-06"]
tech_stack:
  added:
    - "fhir.resources R4B sub-package (already installed in 02-01)"
    - "pymongo AsyncMongoClient (already installed in 02-01)"
  patterns:
    - "R4B-only import via fhir.resources.R4B.* with __all__ gate (Pitfall 1 guard)"
    - "AsyncMongoClient upsert (replace_one upsert=True) — idempotent save"
    - "Compound indexes at startup (Pitfall 6 guard)"
    - "tz-aware Provenance.recorded via datetime.now(timezone.utc).isoformat() (Pitfall 9)"
key_files:
  created:
    - libs/veridoc-fhir/src/veridoc_fhir/models.py
    - libs/veridoc-fhir/src/veridoc_fhir/extensions.py
    - libs/veridoc-fhir/src/veridoc_fhir/provenance.py
    - libs/veridoc-fhir/src/veridoc_fhir/repository.py
    - libs/veridoc-fhir/tests/test_models.py
    - libs/veridoc-fhir/tests/test_provenance.py
    - libs/veridoc-fhir/tests/test_repository.py
  modified:
    - libs/veridoc-fhir/src/veridoc_fhir/__init__.py
decisions:
  - "Used get_resource_type() method (not .resource_type attribute) — fhir.resources R4B API uses private __resource_type__ attribute; get_resource_type() is the stable accessor"
  - "valueDecimal returns decimal.Decimal not float — test comparison uses float(ocr_exts[0].valueDecimal)"
  - "motor 'not in source' test narrowed to import lines only — docstring mentions motor as excluded; guard checks import statements not comments"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-11"
  tasks_completed: 2
  files_created: 7
  files_modified: 1
---

# Phase 02 Plan 03: FHIR R4B Model Lib + MongoDB Repository Summary

**One-liner:** FHIR R4B model facade with `__all__` R5 guard + AsyncMongoClient FhirRepository with compound indexes + spec-native Provenance factory with OCR confidence extensions.

## What Was Built

### Task 1: R4B model facade + extension constants + provenance factory

**Commits:** `a9dcc09` (RED), `76c6f65` (GREEN)

**`libs/veridoc-fhir/src/veridoc_fhir/models.py`** — re-exports all 9 clinical resource types + Provenance from `fhir.resources.R4B.*` (NEVER top-level). The `__all__` gate is the enforcement mechanism preventing future code from accidentally importing R5 classes (Pitfall 1 guard, T-02-FHIR-02).

**`libs/veridoc-fhir/src/veridoc_fhir/extensions.py`** — canonical extension URL constants:
- `OCR_CONFIDENCE_URL = "urn:veridoc:extension:ocr-confidence"`
- `INGESTION_PATH_URL = "urn:veridoc:extension:ingestion-path"`
- `ALCOA_LEGIBILITY_FLAG_URL = "urn:veridoc:extension:alcoa-legibility-flag"`

**`libs/veridoc-fhir/src/veridoc_fhir/provenance.py`** — `create_provenance(target_ref, source, ingestion_path, actor_ref, ocr_confidence=None)`:
- `recorded` uses `datetime.now(timezone.utc).isoformat()` (Pitfall 9 guard)
- `ingestion-path` extension always present
- `ocr-confidence` extension present only when `ocr_confidence is not None` (0.0 is valid)
- `entity.what.reference` carries the source URN (never a natural_id, T-02-FHIR-03)
- `meta.source` set on the Provenance resource itself

**Tests:** 38 tests pass (26 model tests + 12 provenance tests).

### Task 2: FhirRepository (AsyncMongoClient) + indexes + round-trip test

**Commits:** `1f1450e` (RED), `de7bfb0` (GREEN)

**`libs/veridoc-fhir/src/veridoc_fhir/repository.py`** — `FhirRepository`:
- `AsyncMongoClient` (NOT motor — deprecated EOL 2026-05-14, Pitfall 2)
- `create_indexes()` creates:
  - `(resourceType, id)` — unique (idempotency guard + T-02-FHIR-04)
  - `(resourceType, subject.reference)` — patient query index
  - `(resourceType, meta.source)` — provenance source query
  - `id` — single-field for fast ID lookup
- `save(resource)` — `replace_one upsert=True` on `{resourceType, id}` (idempotent)
- `find_by_patient(patient_id, resource_type)` — queries indexed compound path (no COLLSCAN)

**Tests:** 2 source-inspection tests pass; 5 integration tests skip cleanly without Docker (conftest.py `mongo_url` fixture handles graceful skip).

## Verification Results

```
uv run pytest libs/veridoc-fhir -q --import-mode=importlib
........................................sssss  [100%]
40 passed, 5 skipped
```

Source inspection verification:
- `models.py` confirmed to import from `fhir.resources.R4B` (not top-level R5)
- `repository.py` confirmed: `AsyncMongoClient` present, `motor` not in imports
- `models.__all__` confirmed to contain all 10 classes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] fhir.resources API: `.resource_type` attribute does not exist**
- **Found during:** Task 1 GREEN phase
- **Issue:** Tests used `resource.resource_type` (standard-looking attribute) but `fhir.resources` uses `resource.get_resource_type()` (method) or `resource.__resource_type__` (private attribute). The `.resource_type` access raises `AttributeError`.
- **Fix:** All 10 test assertions changed to use `resource.get_resource_type()` (the stable public accessor method).
- **Files modified:** `test_models.py`, `test_provenance.py`
- **Commit:** `76c6f65`

**2. [Rule 1 - Bug] `valueDecimal` returns `decimal.Decimal` not `float`**
- **Found during:** Task 1 GREEN phase (provenance OCR confidence test)
- **Issue:** `abs(ocr_exts[0].valueDecimal - 0.97)` raised `TypeError` — `decimal.Decimal - float` is unsupported.
- **Fix:** Comparison wrapped with `float()`: `abs(float(ocr_exts[0].valueDecimal) - 0.97) < 1e-6`
- **Files modified:** `test_provenance.py`
- **Commit:** `76c6f65`

**3. [Rule 1 - Bug] Motor 'not in source' guard matched comments**
- **Found during:** Task 2 GREEN phase
- **Issue:** The test `assert "motor" not in source` matched the docstring comment "NOT motor (deprecated...)" in `repository.py`, causing a false failure.
- **Fix:** Test narrowed to check only `import` and `from` lines (not all source lines), ensuring the guard catches actual motor imports while ignoring explanatory comments.
- **Files modified:** `test_repository.py`
- **Commit:** `de7bfb0`

## Known Stubs

None. All public API functions are fully implemented.

## Threat Flags

None. No new network endpoints or trust boundaries introduced. The `FhirRepository` connects to MongoDB (existing boundary in threat model), and all FHIR resources are validated by `fhir.resources.R4B` Pydantic v2 before save (T-02-FHIR-01 mitigated).

## Self-Check: PASSED

All created files confirmed present:
- FOUND: models.py
- FOUND: extensions.py
- FOUND: provenance.py
- FOUND: repository.py
- FOUND: test_models.py
- FOUND: test_provenance.py
- FOUND: test_repository.py

All commits confirmed:
- FOUND: a9dcc09 (RED: failing tests for models/provenance)
- FOUND: 76c6f65 (GREEN: R4B model facade + extensions + provenance)
- FOUND: 1f1450e (RED: failing tests for repository)
- FOUND: de7bfb0 (GREEN: FhirRepository implementation)
