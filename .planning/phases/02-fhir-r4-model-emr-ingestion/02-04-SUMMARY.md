---
phase: 02-fhir-r4-model-emr-ingestion
plan: "04"
subsystem: veridoc-ingestion
tags: [ingestion, adapter, ocr, blob-store, abc, tdd, alcoa]
dependency_graph:
  requires: [02-01]
  provides: [02-05]
  affects: [veridoc-ingestion]
tech_stack:
  added:
    - pytesseract>=0.3.13 (already in pyproject.toml from 02-01)
    - boto3>=1.43.0 (already in pyproject.toml from 02-01)
    - Pillow>=9.0 (already in pyproject.toml from 02-01)
  patterns:
    - ABC + local-impl + cloud-stubs (mirrors veridoc-crypto/kms.py)
    - StrEnum for modality constants
    - Frozen dataclass for per-site config
    - TDD RED/GREEN for all three tasks
key_files:
  created:
    - libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/registry.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/__init__.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/proprietary.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/ocr_engine.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/blob_store.py
    - libs/veridoc-ingestion/tests/test_registry.py
    - libs/veridoc-ingestion/tests/test_ocr_engine.py
    - libs/veridoc-ingestion/tests/test_blob_store.py
  modified:
    - libs/veridoc-ingestion/src/veridoc_ingestion/__init__.py
decisions:
  - "D-05: SourceAdapter ABC + SourceProfile frozen dataclass + SourceProfileRegistry wired"
  - "D-07/D-08: OcrEngine ABC + TesseractEngine working impl via pytesseract.image_to_data"
  - "D-10: BlobStore ABC + S3BlobStore with endpoint_url MinIO/S3 portability"
  - "D-11: ProprietaryAdapter interface stub raises NotImplementedError"
  - "ALCOA-01: flagged<0.95, escalated<0.85 thresholds enforced server-side in OcrResult"
metrics:
  duration: "~6 minutes"
  completed: "2026-06-11"
  tasks_completed: 3
  tasks_total: 3
  files_created: 9
  files_modified: 1
---

# Phase 02 Plan 04: Ingestion Contracts + Portable Abstractions Summary

**One-liner:** SourceAdapter ABC + SourceProfileRegistry, TesseractEngine OCR with ALCOA legibility flags, and MinIO-compatible S3BlobStore — all following the kms.py ABC+local-impl+cloud-stubs pattern.

---

## What Was Built

Three abstraction layers for the `veridoc-ingestion` lib built via TDD (RED/GREEN for each task):

**Task 1 — Ingestion contract (D-05/D-11):**
- `adapter.py`: `SourceModality` StrEnum (5 members), `SourceProfile` frozen dataclass, `SourceAdapter` ABC with abstract `ingest()` mirroring kms.py docstring discipline.
- `registry.py`: `SourceProfileRegistry.register()/get()/get_adapter()` — raises descriptive `LookupError` (not bare `KeyError`) for unknown sites; routes `PROPRIETARY` to `ProprietaryAdapter`.
- `adapters/proprietary.py`: `ProprietaryAdapter` conforms to `SourceAdapter`, raises `NotImplementedError` with wire-when message, marked `# pragma: no cover - no real contract to test (D-11)`.

**Task 2 — OcrEngine (D-07/D-08):**
- `ocr_engine.py`: `OcrResult` dataclass (text, document_confidence, word_confidences, flagged, escalated); `OcrEngine` ABC; `TesseractEngine` using `pytesseract.image_to_data` (not subprocess — per RESEARCH anti-pattern); `TextractEngine` + `AzureDocumentIntelligenceEngine` stubs with `# pragma: no cover - DEC-cloud-provider OPEN`.
- ALCOA thresholds: `flagged = doc_conf < 0.95`, `escalated = doc_conf < 0.85` — server-computed from raw pytesseract output (T-02-OCR-01 mitigated).

**Task 3 — BlobStore (D-10):**
- `blob_store.py`: `BlobStore` ABC; `S3BlobStore` using boto3 with `endpoint_url` conditional for MinIO/real-S3 portability; `AzureBlobStore` stub with `# pragma: no cover - DEC-cloud-provider OPEN`.
- `put()` returns `s3://{bucket}/{key}` URI; keys are caller-supplied (UUID+site_id for T-02-BLOB-01 non-enumerability).

---

## Test Results

```
libs/veridoc-ingestion: 21 tests total
  8 passed  (test_registry.py — all pass, no external deps)
  6 passed  (test_blob_store.py — abstract/stub tests pass; MinIO tests skip without Docker)
  3 skipped (test_blob_store.py — Docker/MinIO not available in dev)
  7 passed  (test_ocr_engine.py — abstract/stub/OcrResult tests pass)
  4 skipped (test_ocr_engine.py — tesseract binary not on PATH)
```

MinIO integration tests (test_blob_store.py) and Tesseract live-OCR tests (test_ocr_engine.py) skip cleanly without Docker/binary — as required by plan notes.

---

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 7efb410 | test | RED: test_registry.py failing tests |
| 5f811c4 | feat | GREEN: SourceAdapter/SourceProfile/SourceProfileRegistry/ProprietaryAdapter |
| c59af27 | test | RED: test_ocr_engine.py failing tests |
| e45719a | feat | GREEN: OcrEngine/TesseractEngine/cloud stubs |
| b2eb17e | test | RED: test_blob_store.py failing tests |
| 47fee2d | feat | GREEN: BlobStore/S3BlobStore/AzureBlobStore stub |
| 91ef7c5 | chore | Public API update in __init__.py |

---

## Deviations from Plan

None — plan executed exactly as written.

The `# pragma: no cover` annotation on `ProprietaryAdapter` class is placed on the class line (matching the kms.py pattern for `AwsKmsKeyring`) rather than on `ingest()` only, which is consistent with the plan's stated pattern and the existing codebase convention.

---

## TDD Gate Compliance

All three tasks followed RED → GREEN sequence:

1. Task 1: RED commit `7efb410` → GREEN commit `5f811c4`
2. Task 2: RED commit `c59af27` → GREEN commit `e45719a`
3. Task 3: RED commit `b2eb17e` → GREEN commit `47fee2d`

---

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `ProprietaryAdapter.ingest` | adapters/proprietary.py | D-11: no vendor contract yet; raises NotImplementedError |
| `TextractEngine.extract` | ocr_engine.py | DEC-cloud-provider OPEN to AWS |
| `AzureDocumentIntelligenceEngine.extract` | ocr_engine.py | DEC-cloud-provider OPEN to Azure |
| `AzureBlobStore.put/get` | blob_store.py | DEC-cloud-provider OPEN to Azure |

These stubs are intentional and documented; they will be wired when DEC-cloud-provider closes.

---

## Threat Surface Scan

All mitigations from the plan's threat register are implemented:

| Threat ID | Mitigation Implemented |
|-----------|----------------------|
| T-02-OCR-01 | `flagged`/`escalated` computed server-side in `OcrResult`; never user-supplied |
| T-02-OCR-02 | `TesseractEngine` reads bytes via `PIL.Image.open()` + pytesseract only; never executed |
| T-02-BLOB-01 | Key non-guessability documented as caller responsibility; test uses `uuid4()` keys |
| T-02-BLOB-02 | `endpoint_url` conditional keeps DEC-cloud-provider OPEN; Azure path stubbed |

No new threat surface beyond what was listed in the plan's threat model.

---

## Self-Check: PASSED

Files exist:
- libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py: FOUND
- libs/veridoc-ingestion/src/veridoc_ingestion/registry.py: FOUND
- libs/veridoc-ingestion/src/veridoc_ingestion/adapters/__init__.py: FOUND
- libs/veridoc-ingestion/src/veridoc_ingestion/adapters/proprietary.py: FOUND
- libs/veridoc-ingestion/src/veridoc_ingestion/ocr_engine.py: FOUND
- libs/veridoc-ingestion/src/veridoc_ingestion/blob_store.py: FOUND
- libs/veridoc-ingestion/tests/test_registry.py: FOUND
- libs/veridoc-ingestion/tests/test_ocr_engine.py: FOUND
- libs/veridoc-ingestion/tests/test_blob_store.py: FOUND

Commits verified in git log (hashes 7efb410 through 91ef7c5).
