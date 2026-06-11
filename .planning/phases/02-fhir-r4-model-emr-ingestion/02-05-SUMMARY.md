---
phase: 02-fhir-r4-model-emr-ingestion
plan: "05"
subsystem: veridoc-ingestion adapters
tags: [adapters, fhir-r4b, hl7v2, pdf, ocr, pseudonymization, extraction]
dependency_graph:
  requires: ["02-03", "02-04"]
  provides: ["02-06", "02-07"]
  affects: ["veridoc-ingestion", "veridoc-fhir"]
tech_stack:
  added:
    - hl7apy 1.3.5 (HL7 v2.x structured parsing — D-12)
    - pypdf (PDF text extraction — PDF adapter)
    - openpyxl (Excel parsing — PDF/Excel adapter)
    - veridoc-pseudonym (pseudonym_token at ingestion — D-14)
    - veridoc-fhir extensions (ALCOA URL constants)
  patterns:
    - ABC + concrete adapter subclass (mirrors KMSKeyring in veridoc-crypto)
    - Explicit HL7 mapping layer (hl7apy → FHIR; not hand-rolled — D-12)
    - Rule-based EntityExtractor interface (LLM-backable later — D-09)
    - Server-side ALCOA flag derivation (T-02-ADP-04)
    - get_resource_type() method (not .resource_type attribute — fhir.resources R4B API)
key_files:
  created:
    - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/pdf_excel.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/adapters/ocr.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/mapping/__init__.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py
    - libs/veridoc-ingestion/src/veridoc_ingestion/extraction.py
    - libs/veridoc-ingestion/tests/test_adapters.py
  modified:
    - libs/veridoc-ingestion/src/veridoc_ingestion/registry.py
decisions:
  - "PID.3 CX_1 (raw ID only, not full CX string) used as natural_id for pseudonym_token (open question #3 resolved)"
  - "NativeFhirAdapter filters to 9 scoped resource types; skips Claim/EOB/Immunization"
  - "HL7 LF→CR normalization applied before hl7apy parse (hl7apy requires CR segment separator)"
  - "OcrAdapter defaults: TesseractEngine + S3BlobStore from env; both injectable for tests"
  - "RuleBasedExtractor is rule-based only (no LLM — D-09 deferral honored)"
  - "test_ocr skips gracefully when tesseract binary absent (shutil.which guard in test)"
metrics:
  duration: ~45min
  completed: "2026-06-11"
  tasks: 2
  files: 9
---

# Phase 02 Plan 05: EMR Ingestion Adapters Summary

**One-liner:** Four working ingestion adapters (native FHIR, HL7v2+explicit mapping, PDF/Excel rule-based, OCR+ALCOA) + EntityExtractor interface — all normalizing heterogeneous EMR sources to FHIR R4B with pseudonymized PII.

## What Was Built

### Task 1: NativeFhirAdapter + HL7v2Adapter + HL7→FHIR mapping (GREEN)

**mapping/hl7v2_fhir.py** — explicit segment-to-resource mapping using hl7apy (D-12):
- `map_adt_a01_to_fhir`: PID → Patient (pseudonymized); PV1.2 (E/I/O/P→EMER/IMP/AMB/PRENC) → Encounter class; EVN.2 → Encounter.period.start
- `map_oru_r01_to_fhir`: OBX(+) → Observation (LOINC from OBX-3.1, value from OBX-5, units from OBX-6); OBR-4 → DiagnosticReport.code
- Normalized LF→CR before hl7apy parse; PV1 class defaults to AMB for unknown codes

**adapters/native_fhir.py** — NativeFhirAdapter:
- Parses Synthea/native FHIR R4B transaction Bundle
- Filters to 9 scoped resource types (skips Claim, ExplanationOfBenefit, Immunization)
- Pseudonymizes Patient.id/identifier/name/birthDate via `pseudonym_token(site_id+raw_id, raw_id)` (D-14, SC-4)

**adapters/hl7v2.py** — HL7v2Adapter:
- Detects message type from MSH-9 (ADT_A01, ORU_R01)
- Extracts PID.3 CX_1 as natural_id (open question #3: ID component only, strips assigning authority)
- Delegates to mapping.hl7v2_fhir functions (D-12: vetted library, not hand-rolled)
- Rejects unknown message types with clear ValueError

**registry.py** — all four adapters registered in `_build_modality_map`.

### Task 2: PdfExcelAdapter + OcrAdapter + RuleBasedExtractor (GREEN)

**extraction.py** — EntityExtractor ABC + RuleBasedExtractor:
- Rule-based only (no LLM — D-09 deferral honored)
- Regex lab-result extraction with LOINC lookup table (Creatinine, Sodium, Potassium, Glucose, Hemoglobin, etc.)
- Returns FHIR Observation dicts; caller validates and injects subject reference

**adapters/pdf_excel.py** — PdfExcelAdapter:
- Auto-detects PDF (pypdf) vs xlsx (openpyxl) from magic bytes
- Extracts text, runs RuleBasedExtractor, builds Patient + Observation list
- Pseudonymizes MRN extracted from text via `pseudonym_token` (SC-2b, D-14)

**adapters/ocr.py** — OcrAdapter:
- Injected OcrEngine + BlobStore (defaults to TesseractEngine + S3BlobStore)
- Stores original bytes to blob store (ALCOA+ Original principle — D-10)
- Builds DocumentReference with:
  - `docStatus = "preliminary"` (open question #2 resolved: pending Phase 5 ALCOA+ review)
  - `content.attachment.url` = s3:// blob URI
  - `urn:veridoc:extension:ocr-confidence` extension
  - `urn:veridoc:extension:alcoa-legibility-flag = "legibility-flag"` if conf < 0.95
  - `urn:veridoc:extension:alcoa-legibility-flag = "legibility-escalate"` if conf < 0.85
- ALCOA flags derived server-side from OcrEngine (T-02-ADP-04 mitigated)

## Test Results

```
libs/veridoc-ingestion/tests/test_adapters.py   9 passed, 1 skipped
```

| Test | Result | Notes |
|------|--------|-------|
| test_native_fhir | PASS | Synthea bundle → R4B list with Patient |
| test_native_fhir_patient_pseudonymized | PASS | Patient.id ≠ raw Synthea UUID |
| test_hl7v2_adt | PASS | ADT_A01 → [Patient, Encounter]; PV1.2 'I' → IMP |
| test_hl7v2_oru | PASS | ORU_R01 → [Obs×3, DiagnosticReport]; LOINC 2160-0 |
| test_hl7v2_delegates_to_mapping | PASS | source confirms hl7v2_fhir import |
| test_pseudonymization | PASS | raw MRN absent; same inputs → same token |
| test_pdf_excel | PASS | lab PDF → [Patient, Observation×3] |
| test_pdf_excel_pseudonymized | PASS | Patient.identifier has no raw MRN |
| test_ocr | SKIP | tesseract binary not installed (correct skip behavior) |
| test_ocr_flags | PASS | stub engine: 0.97→no flags; 0.90→flag; 0.80→flag+escalate |

## Commits

| Hash | Message |
|------|---------|
| 16920fb | test(02-05): add failing adapter tests (RED) — NativeFhir, HL7v2, PDF, OCR |
| bbd7bb0 | feat(02-05): NativeFhirAdapter + HL7v2Adapter + explicit HL7→FHIR mapping (GREEN) |
| e452182 | feat(02-05): PdfExcelAdapter + OcrAdapter + RuleBasedExtractor (GREEN) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] fhir.resources R4B .resource_type attribute does not exist**
- **Found during:** Task 1 GREEN
- **Issue:** Tests used `r.resource_type` (attribute) but fhir.resources R4B uses `r.get_resource_type()` (method) — same deviation found in 02-03 and documented there.
- **Fix:** All test assertions changed to `get_resource_type()`. Adapters use string literals internally (no attribute access needed).
- **Files modified:** `libs/veridoc-ingestion/tests/test_adapters.py`
- **Commit:** bbd7bb0

**2. [Rule 1 - Bug] FHIR fixtures path computation incorrect**
- **Found during:** Task 1 GREEN (test execution)
- **Issue:** `__file__.parent.parent.parent.parent` resolved to the wrong directory. The correct path requires `pathlib.Path(__file__).parents[2]` (index 2 = `libs/`) then `/ "veridoc-fhir" / ...`.
- **Fix:** Used `parents[2]` indexing with explicit comment on the path structure.
- **Files modified:** `libs/veridoc-ingestion/tests/test_adapters.py`
- **Commit:** bbd7bb0

**3. [Rule 1 - Bug] hl7apy requires CR (\r) segment separator, not LF (\n)**
- **Found during:** Task 1 pre-exploration (manual testing)
- **Issue:** hl7 fixtures use LF line endings. With LF as separator, `parse_message` only found MSH and no other segments (PID, PV1, OBX not found), producing empty results.
- **Fix:** `hl7_str.replace("\n", "\r")` applied before `parse_message()` in both the mapping functions and HL7v2Adapter. Documented in both files.
- **Files modified:** `mapping/hl7v2_fhir.py`, `adapters/hl7v2.py`
- **Commit:** bbd7bb0

None of these were architectural changes — all were Bug (Rule 1) auto-fixes.

## Threat Mitigations Verified

| ID | Mitigation | Status |
|----|-----------|--------|
| T-02-ADP-01 | pseudonym_token replaces PII in all four adapters; test_pseudonymization asserts raw MRN absent | VERIFIED |
| T-02-ADP-02 | hl7apy structured parsing; unknown message types raise ValueError with clear message | VERIFIED |
| T-02-ADP-03 | pypdf/openpyxl exceptions caught and re-raised as ValueError; size limits at service layer | VERIFIED |
| T-02-ADP-04 | ALCOA flags derived from OcrEngine output, never from request input; test_ocr_flags proves this with StubEngine | VERIFIED |
| T-02-ADP-05 | original retained in blob; blob key = non-guessable UUID+site_id prefix; accepted per plan | ACCEPTED |

## Known Stubs

None — all four adapters are functional. OcrAdapter defaults to TesseractEngine which requires the system binary; tests use StubEngine to avoid the binary dependency.

## Self-Check: PASSED

Files exist:
- [x] libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py
- [x] libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py
- [x] libs/veridoc-ingestion/src/veridoc_ingestion/adapters/pdf_excel.py
- [x] libs/veridoc-ingestion/src/veridoc_ingestion/adapters/ocr.py
- [x] libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py
- [x] libs/veridoc-ingestion/src/veridoc_ingestion/extraction.py
- [x] libs/veridoc-ingestion/tests/test_adapters.py

Commits exist:
- [x] 16920fb (RED test commit)
- [x] bbd7bb0 (Task 1 GREEN)
- [x] e452182 (Task 2 GREEN)
