---
phase: 02-fhir-r4-model-emr-ingestion
plan: "01"
subsystem: fhir-model, emr-ingestion, fixtures
tags: [fhir, fhir-r4b, pymongo, rq, hl7apy, pytesseract, boto3, synthea, testcontainers, mongodb, minio]

requires:
  - phase: 01-platform-skeleton
    provides: "uv workspace, audit SDK, pseudonym lib, crypto lib, auth lib, tenancy lib, reference service"

provides:
  - "veridoc-fhir workspace lib registered with fhir.resources>=8.2.0 + pymongo>=4.17.0"
  - "veridoc-ingestion workspace lib registered with rq/hl7apy/pytesseract/boto3/openpyxl/pypdf"
  - "5 Synthea R4B transaction Bundle fixtures (seed 42, use_us_core_ig=false) + hand-crafted AdverseEvent"
  - "HL7 ADT_A01 + ORU_R01 fixtures (hl7apy-validated), PDF lab report, legible + illegible scan PNGs"
  - "libs/veridoc-fhir/tests/conftest.py: session-scoped mongo_url (MongoDbContainer)"
  - "libs/veridoc-ingestion/tests/conftest.py: session-scoped minio_endpoint (MinioContainer) + eager_rq_queue"
  - "scripts/gen_synthea_fixtures.sh: reproducible Synthea generation (seed 42, Pitfall 7 guarded)"
  - "Phase 02 PACKAGE-LEGITIMACY.md section: all 9 packages APPROVED by human reviewer"

affects:
  - "02-02 (FHIR R4B model layer): uses fhir.resources R4B + Synthea fixtures"
  - "02-03 (SourceAdapter + adapters): uses HL7/PDF/image fixtures + veridoc-ingestion lib"
  - "02-04 (OCR engine): uses image fixtures + Tesseract"
  - "02-05 (ingestion service): uses both libs + conftests"
  - "02-06 (Helm MongoDB/MinIO): no direct dep"

tech-stack:
  added:
    - "fhir.resources 8.2.0 — FHIR R4B Pydantic v2 model library (R4B sub-package, not top-level)"
    - "pymongo 4.17.0 — async MongoDB driver (AsyncMongoClient; motor deprecated)"
    - "rq 2.9.1 — Redis job queue with JSONSerializer"
    - "hl7apy 1.3.5 — HL7 v2.x message parser (CRS4-official)"
    - "pytesseract 0.3.13 — Tesseract OCR Python wrapper"
    - "Pillow 12.2.0 — PIL image library (pytesseract transitive dep; used for fixture generation)"
    - "boto3 1.43.27 — S3-compatible blob client (MinIO + real S3 via endpoint_url)"
    - "openpyxl 3.1.5 — Excel .xlsx parsing"
    - "pypdf 6.13.2 — PDF text extraction (used to generate lab_report.pdf fixture)"
    - "Synthea JAR (master-branch-latest) — synthetic FHIR R4B patient bundle generation"
  patterns:
    - "hatchling minimal lib pattern (veridoc-fhir, veridoc-ingestion mirror veridoc-crypto)"
    - "uv [tool.uv.sources] workspace entry pattern for new libs"
    - "Three-path testcontainer resolution: env var → testcontainers → pytest.skip"
    - "Session-scoped container fixture + function-scoped collection teardown"
    - "Synthea -s 42 + use_us_core_ig=false for reproducible FHIR R4B fixtures (Pitfall 7)"

key-files:
  created:
    - "libs/veridoc-fhir/pyproject.toml"
    - "libs/veridoc-fhir/README.md"
    - "libs/veridoc-fhir/src/veridoc_fhir/__init__.py"
    - "libs/veridoc-fhir/tests/conftest.py"
    - "libs/veridoc-fhir/tests/fixtures/fhir/adverse_event.json"
    - "libs/veridoc-fhir/tests/fixtures/fhir/[5 Synthea R4B bundle JSONs]"
    - "libs/veridoc-ingestion/pyproject.toml"
    - "libs/veridoc-ingestion/README.md"
    - "libs/veridoc-ingestion/src/veridoc_ingestion/__init__.py"
    - "libs/veridoc-ingestion/tests/conftest.py"
    - "libs/veridoc-ingestion/tests/fixtures/hl7/adt_a01.hl7"
    - "libs/veridoc-ingestion/tests/fixtures/hl7/oru_r01.hl7"
    - "libs/veridoc-ingestion/tests/fixtures/pdf/lab_report.pdf"
    - "libs/veridoc-ingestion/tests/fixtures/images/scan_legible.png"
    - "libs/veridoc-ingestion/tests/fixtures/images/scan_illegible.png"
    - "scripts/gen_synthea_fixtures.sh"
  modified:
    - "pyproject.toml — added veridoc-fhir + veridoc-ingestion to [tool.uv.sources]"
    - "uv.lock — updated with all 9 new packages"
    - "docs/validation/PACKAGE-LEGITIMACY.md — Phase 02 section (Task 1, prior checkpoint)"

key-decisions:
  - "DEC-pymongo-asyncclient: Use pymongo AsyncMongoClient (not motor; motor EOL 2026-05-14)"
  - "DEC-fhir-r4b-subpackage: Always import fhir.resources.R4B.* — top-level targets R5 since v7"
  - "DEC-rq-json-serializer: RQ with JSONSerializer only; no pickle (RCE risk)"
  - "DEC-synthea-seed42: -s 42 + use_us_core_ig=false for reproducible R4B fixtures (Pitfall 7)"
  - "DEC-motor-absent: motor explicitly excluded; uv.lock asserted free of motor (T-02-01)"

requirements-completed: [EMR-01]

duration: ~25min (Tasks 2-3 only; Task 1 was prior checkpoint)
completed: "2026-06-11"
---

# Phase 02 Plan 01: Wave 0 Foundation Summary

**Two new hatchling workspace libs registered (veridoc-fhir + veridoc-ingestion), all 9 Phase 02 packages installed and importable, 5 Synthea R4B transaction Bundle fixtures committed alongside a hand-crafted AdverseEvent, HL7/PDF/image fixtures hand-crafted, and Mongo/MinIO testcontainer conftests wired — unblocking all Wave 2-5 plans.**

## Performance

- **Duration:** ~25 min (Tasks 2 & 3; Task 1 was approved at prior checkpoint)
- **Started:** 2026-06-11T18:15:00Z
- **Completed:** 2026-06-11T18:45:09Z
- **Tasks completed:** 2 of 3 (Task 1 completed at prior checkpoint)
- **Files created/modified:** 22

## Accomplishments

### Task 2: Register new libs + install approved packages (commit c00b9aa)

- Created `libs/veridoc-fhir/pyproject.toml` — hatchling, `fhir.resources>=8.2.0` + `pymongo>=4.17.0`
- Created `libs/veridoc-ingestion/pyproject.toml` — hatchling, `rq/hl7apy/pytesseract/boto3/openpyxl/pypdf` + workspace deps on veridoc-fhir/pseudonym/audit
- Added both to root `pyproject.toml` `[tool.uv.sources]` as `{ workspace = true }`
- Ran `uv sync --all-packages`; all 9 packages installed and importable
- `motor` absent from `uv.lock` (T-02-01 mitigated)
- `fhir.resources.R4B.Patient` imports successfully (critical R4B sub-package discipline)

### Task 3: Generate fixtures + shared testcontainer conftests (commit 1adae2e)

**FHIR fixtures (`libs/veridoc-fhir/tests/fixtures/fhir/`):**
- 5 Synthea R4B transaction Bundle JSONs generated (Java OpenJDK 21; seed 42; `use_us_core_ig=false`)
- All 5 parse as `fhir.resources.R4B.Bundle` without error
- `adverse_event.json`: hand-crafted R4B AdverseEvent (Synthea gap A7) — validates as `fhir.resources.R4B.AdverseEvent`

**Ingestion fixtures (`libs/veridoc-ingestion/tests/fixtures/`):**
- `hl7/adt_a01.hl7`: MSH+EVN+PID+NK1+PV1+DG1 — parses with `hl7apy.parser.parse_message`
- `hl7/oru_r01.hl7`: MSH+PID+OBR+3×OBX (LOINC codes for creatinine/sodium/potassium) — parses with hl7apy
- `pdf/lab_report.pdf`: pypdf-generated PDF with extractable text layer (lab result table)
- `images/scan_legible.png`: 800×600 high-contrast black-on-white printed text (high OCR confidence expected)
- `images/scan_illegible.png`: 800×600 blurred, low-contrast (GaussianBlur r=4 + Contrast 0.3×) — low OCR confidence expected

**Conftests:**
- `libs/veridoc-fhir/tests/conftest.py`: session-scoped `mongo_url` (MongoDbContainer "mongo:7-jammy") + function-scoped `clean_fhir_collection` (drops fhir_resources between tests)
- `libs/veridoc-ingestion/tests/conftest.py`: session-scoped `minio_endpoint` (MinioContainer) + `eager_rq_queue` (fakeredis/sync fallback for worker tests)

**Synthea script:**
- `scripts/gen_synthea_fixtures.sh`: downloads JAR, runs `-p 5 -s 42 --exporter.fhir.use_us_core_ig=false`, copies patient bundles to fixtures dir (skips hospitalInformation/practitionerInformation)

## Commits

| Commit | Task | Description |
|--------|------|-------------|
| 56679f2 | T1 | chore(02-01): add Phase 02 package legitimacy table |
| 870fcb6 | T1 | docs(02-01): approve all 9 Phase 02 packages |
| c00b9aa | T2 | feat(02-01): register veridoc-fhir + veridoc-ingestion libs |
| 1adae2e | T3 | feat(02-01): Wave 0 fixtures + Mongo/MinIO testcontainer conftests |

## Deviations from Plan

### Auto-deviation: README.md files added

**Found during:** Task 2
**Issue:** Hatchling `readme = "README.md"` in pyproject.toml causes `OSError: Readme file does not exist: README.md` on `uv sync --all-packages`
**Fix:** Created minimal README.md files for both libs before running sync
**Files modified:** `libs/veridoc-fhir/README.md`, `libs/veridoc-ingestion/README.md`
**Rule:** Rule 3 (auto-fix blocking issue)

### Tesseract system package not installed (deviation from plan, no auto-fix)

**Found during:** Task 3
**Issue:** `tesseract` binary not on PATH in the dev environment; `pytesseract.get_tesseract_version()` raises TesseractNotFoundError
**Impact:** Image fixtures (scan_legible.png, scan_illegible.png) created via Pillow only — no actual OCR run at fixture-generation time. The fixtures are valid PNG images with the expected visual properties (high-contrast vs. degraded)
**Not auto-fixed:** Tesseract is a system package (`apt-get install tesseract-ocr`), not a Python package — system installs are outside the executor's scope
**Deferred:** OCR engine tests in plan 02-04 will require `tesseract-ocr` installed. CI must `apt-get install -y tesseract-ocr tesseract-ocr-eng` before running OCR tests (already documented in the Dockerfile pattern in 02-PATTERNS.md)

### Synthea ran via downloaded JAR (not Deviation, matches plan)

Synthea JAR downloaded successfully from `github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar` using OpenJDK 21. 5 patients generated as expected. JAR cached at `.cache/` (not committed; in .gitignore scope).

## Known Stubs

None — this plan creates only scaffold structure (empty `__init__.py` with docstrings), fixtures, and conftests. No business logic stubs.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All new surface is test/fixture code (T-02-02: accepted — Synthea/HL7/PDF fixtures are synthetic, no real PII).

## Self-Check: PASSED

Files confirmed present:
- libs/veridoc-fhir/pyproject.toml: FOUND
- libs/veridoc-fhir/src/veridoc_fhir/__init__.py: FOUND
- libs/veridoc-fhir/tests/conftest.py: FOUND
- libs/veridoc-fhir/tests/fixtures/fhir/adverse_event.json: FOUND (6 FHIR JSON fixtures total)
- libs/veridoc-ingestion/pyproject.toml: FOUND
- libs/veridoc-ingestion/src/veridoc_ingestion/__init__.py: FOUND
- libs/veridoc-ingestion/tests/conftest.py: FOUND
- libs/veridoc-ingestion/tests/fixtures/hl7/adt_a01.hl7: FOUND
- libs/veridoc-ingestion/tests/fixtures/hl7/oru_r01.hl7: FOUND
- libs/veridoc-ingestion/tests/fixtures/pdf/lab_report.pdf: FOUND
- libs/veridoc-ingestion/tests/fixtures/images/scan_legible.png: FOUND
- libs/veridoc-ingestion/tests/fixtures/images/scan_illegible.png: FOUND
- scripts/gen_synthea_fixtures.sh: FOUND

Commits confirmed:
- c00b9aa: FOUND (feat(02-01): register veridoc-fhir + veridoc-ingestion libs)
- 1adae2e: FOUND (feat(02-01): Wave 0 fixtures + Mongo/MinIO testcontainer conftests)
