# Phase 2: FHIR R4 Model & EMR Ingestion — Research

**Researched:** 2026-06-11
**Domain:** FHIR R4B normalization, heterogeneous EMR ingestion, async job queues, OCR/NLP extraction
**Confidence:** HIGH (all standard-stack claims verified against PyPI, official FHIR spec, or official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `fhir.resources` (Pydantic v2 FHIR R4 models) — 9 resource types, full spec validation.
- **D-02:** MongoDB as the clinical-document store; Postgres stays for audit/identity/tenancy.
- **D-03:** Provenance modeled spec-natively via FHIR `Provenance` resource + `resource.meta.source`.
- **D-04:** `veridoc-fhir` lib (model + repository) + `veridoc-ingestion` lib (adapter interface + adapters) + thin `services/ingestion-service` cloned from `reference-service`.
- **D-05:** `SourceProfile` registry + single `SourceAdapter` interface + N implementations.
- **D-06:** Async ingestion via a Redis-backed queue (Redis already in stack); audit/provenance writes happen as jobs progress through `veridoc-audit`.
- **D-07:** Portable `OcrEngine` abstraction, mirroring `veridoc-crypto` KMS pattern.
- **D-08:** Tesseract as OSS default OCR engine via `pytesseract`.
- **D-09:** Scanned path → FHIR `DocumentReference` with OCR confidence + ALCOA+ legibility flags (<95% flag, <85% escalate); clinical-entity extraction interface defined but rule-based only this phase.
- **D-10:** Portable S3-compatible blob store (MinIO local/CI → S3/Azure Blob); `DocumentReference` points to retained original.
- **D-11:** Four paths fully built (native FHIR, HL7 v2.x, semi-manual PDF/Excel, paper/scanned OCR); proprietary-API adapter is interface-only (raises `NotImplemented`).
- **D-12:** HL7 v2.x via `hl7apy` vetted library + explicit mapping layer to FHIR.
- **D-13:** Synthea for synthetic FHIR R4 bundles (native-path test data) + hand-crafted edge cases.
- **D-14:** Pseudonymize PII at ingestion using `veridoc-pseudonym` deterministic tokens; every ingest writes through `veridoc-audit`.

### Claude's Discretion

- Semi-manual PDF/Excel path: same rule-based extraction interface as OCR path; exact extraction rules are researcher/planner's call.
- Exact `SourceAdapter` interface shape, queue/worker mechanism (RQ vs Celery vs custom Redis), Mongo collection/index design, `OcrEngine` interface signature.
- Which precise FHIR resources non-native adapters emit beyond what success criteria mandate.

### Deferred Ideas (OUT OF SCOPE)

- LLM-based clinical-entity extraction (waits for Phase 4 LLM engine).
- Proprietary-API adapter implementation (interface-only this milestone).
- Higher-accuracy / cloud OCR (docTR, PaddleOCR, Textract, Azure DI).
- ALCOA+ legibility *scoring agent* (Phase 5; this phase only emits OCR confidence + flags).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EMR-01 | FHIR R4 canonical model (9 resource types); per-site source modality configurable; 5 ingestion paths all normalizing to FHIR R4; per-unit provenance (source modality + ingestion path + OCR confidence); pseudonymization at ingestion (GDPR Art. 9) | D-01 through D-14 all directly address EMR-01. fhir.resources R4B library confirmed for all 9 resources; MongoDB confirmed as document store; pymongo AsyncMongoClient confirmed; RQ confirmed as queue; hl7apy confirmed as HL7 parser; pytesseract confirmed for OCR; boto3/MinIO confirmed for blob store; Synthea confirmed for fixtures. |
</phase_requirements>

---

## Summary

Phase 2 introduces four new external dependencies (MongoDB, MinIO blob store, Tesseract OCR, Synthea) on top of the Phase 1 Postgres + Redis + Keycloak skeleton, and adds two new Python libraries (`fhir.resources` and `hl7apy`). Every choice has a direct analogue in the existing codebase: the `OcrEngine` abstraction mirrors `veridoc-crypto/kms.py`, the `BlobStore` abstraction mirrors the same `KMSKeyring` pattern, the ingestion-service clones `services/reference-service`, and async jobs still call `append_audit` (same-transaction on the Postgres audit chain is no longer possible in async workers, so a dedicated session is opened per job).

**Critical finding:** `fhir.resources` v7.0+ dropped FHIR R4 (4.0.1) as a top-level import. The FHIR R4 spec is now available as the **R4B (4.3.0) sub-package** (`from fhir.resources.R4B.patient import Patient`). R4B is backward-compatible with R4 for all 9 resources in scope (no changes to Patient, Encounter, Condition, MedicationRequest, AdverseEvent, DocumentReference, Procedure; DiagnosticReport and Observation gained additional reference-target types only). The planner must use the `R4B` import path throughout; top-level `fhir.resources.patient` now targets R5.

**Motor is deprecated** (end-of-life 2026-05-14). Use pymongo's native `AsyncMongoClient` (stable since pymongo 4.13, current 4.17.0) with FastAPI instead.

**Recommended queue: RQ** over Celery for this phase. Redis is already in the stack; RQ is zero-dependency-broker (no additional infrastructure); its job callbacks are sufficient for provenance/audit writes; JSONSerializer eliminates the pickle-RCE risk; sub-100 tasks/sec OCR workload fits RQ perfectly. Celery is the right choice at enterprise scale with multiple brokers — unnecessary complexity here.

**Primary recommendation:** Use `fhir.resources.R4B` throughout; pymongo 4.17 `AsyncMongoClient`; RQ 2.9.1 with JSONSerializer; `boto3` for the blob-store abstraction (MinIO-compatible with `endpoint_url`); `hl7apy` 1.3.5 for HL7 parsing; `pytesseract` 0.3.13 + Tesseract system package for OCR.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FHIR R4B model construction and validation | `libs/veridoc-fhir` (lib tier) | — | Reusable by all downstream services (Phases 4–6); must be independent |
| FHIR document persistence (MongoDB) | `libs/veridoc-fhir` repository layer | `services/ingestion-service` coordinates | Repository pattern isolates Mongo from adapter logic |
| SourceProfile registry + routing | `libs/veridoc-ingestion` (lib tier) | `services/ingestion-service` (runtime) | Config-driven routing belongs in the shared lib, not the service |
| SourceAdapter implementations | `libs/veridoc-ingestion` (lib tier) | — | Adapters are reusable; adapter test fixtures live here |
| Async job queue (Redis/RQ) | `services/ingestion-service` (service tier) | `libs/veridoc-ingestion` (worker functions) | Queue lifecycle owned by service; worker functions are testable in lib |
| OCR (Tesseract/OcrEngine) | `libs/veridoc-ingestion` (lib tier) | — | Portable abstraction; all engines behind one interface |
| Blob store (MinIO/S3) | `libs/veridoc-ingestion` (lib tier) | `services/ingestion-service` (config) | Portable abstraction; mirrors KMS pattern |
| Pseudonymization at ingestion | `libs/veridoc-pseudonym` (existing lib) | Called from `veridoc-ingestion` adapters | Reuse — do not duplicate |
| Audit writes (per-job) | `libs/veridoc-audit` (existing lib) | Called from RQ worker callbacks | Each job opens its own Session; uses `append_audit` |
| Provenance (FHIR Provenance resource) | `libs/veridoc-fhir` repository layer | Created by adapter after resource write | Stored in same MongoDB collection as other resources |
| Deployment (Helm/Terraform) | Infrastructure tier (`deploy/helm/veridoc`) | `deploy/terraform` | New MongoDB + MinIO StatefulSets added to existing chart |
| CI fixture generation (Synthea) | CI / test fixtures | `libs/veridoc-fhir/tests/fixtures/` | Java CLI; committed JSON bundles checked in as test data |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fhir.resources` | 8.2.0 [VERIFIED: PyPI, nazrulworld/fhir.resources] | FHIR R4B Pydantic v2 resource models + validation | Only mature Pydantic v2 FHIR R4 model lib on PyPI; R4 spec locked in project |
| `pymongo` | 4.17.0 [VERIFIED: PyPI, mongodb/mongo-python-driver] | Async MongoDB driver (`AsyncMongoClient`) | MongoDB-official; Motor deprecated May 2026; native async stable since 4.13 |
| `rq` | 2.9.1 [VERIFIED: PyPI, rq/rq] | Redis-backed async job queue | Zero extra infra (Redis already present); simple callbacks; JSONSerializer available |
| `hl7apy` | 1.3.5 [VERIFIED: PyPI, crs4/hl7apy] | HL7 v2.x message parsing + construction | CRS4 official; supports v2.1–2.8.2; field-level access; structured message objects |
| `pytesseract` | 0.3.13 [VERIFIED: PyPI, madmaze/pytesseract] | Tesseract OCR Python wrapper; per-word confidence | Apache-2.0; `image_to_data()` emits per-word confidence; widely used |
| `boto3` | 1.43.27 [VERIFIED: PyPI, boto/boto3] | S3-compatible blob client; works with MinIO via `endpoint_url` | AWS-official SDK; MinIO is S3-API-compatible; one client, two deployment targets |
| `openpyxl` | 3.1.5 [VERIFIED: PyPI] | Excel (.xlsx) parsing for semi-manual import | MIT; well-maintained; standard Python Excel library |
| `pypdf` | 6.13.2 [VERIFIED: PyPI, py-pdf/pypdf] | PDF text extraction for semi-manual import | Actively maintained successor to PyPDF2; Apache-2.0 |

### Supporting (dev / test only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `testcontainers` | already APPROVED | Ephemeral MongoDB + MinIO in integration tests | Tests that require real Mongo/MinIO |
| Tesseract system package | 5.3.4+ (Ubuntu) | OCR engine binary | Docker image + CI apt install |
| Synthea JAR | latest release | Synthetic FHIR R4B patient bundles | CI fixture generation (not a Python package) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `rq` | Celery 5.6.3 | Celery is more powerful (multiple brokers, scheduling, task routing) but requires broker config, more complex setup; unnecessary for sub-100 tasks/sec OCR workload |
| `rq` | `arq` (async-native RQ) | `arq` is asyncio-native and more idiomatic with FastAPI but less mature; RQ's fork-based workers are fine for CPU-bound OCR tasks |
| `pymongo AsyncMongoClient` | `motor` 3.7.1 | Motor is deprecated (EOL 2026-05-14); pymongo AsyncMongoClient is the official successor |
| `boto3` | `minio` 7.2.20 (MinIO SDK) | MinIO SDK is MinIO-specific; boto3 works with both MinIO (via `endpoint_url`) and real S3/Azure Blob (via adapters), keeping DEC-cloud-provider portable |
| `hl7apy` | `hl7` 0.4.5 (python-hl7) | python-hl7 last released March 2022 (stale); hl7apy released March 2024, supports v2.1–2.8.2, structured message objects |

**Installation (new packages only — add to `veridoc-ingestion` and `veridoc-fhir` pyproject.toml):**

```bash
# veridoc-fhir lib
uv add "fhir.resources>=8.2.0" "pymongo>=4.17.0"

# veridoc-ingestion lib
uv add "rq>=2.9.1" "hl7apy>=1.3.5" "pytesseract>=0.3.13" "boto3>=1.43.0" "openpyxl>=3.1.5" "pypdf>=6.13.0"

# System dependency (Dockerfile + CI)
# apt-get install -y tesseract-ocr tesseract-ocr-eng
```

---

## Package Legitimacy Audit

> slopcheck was unavailable at research time. All packages below are tagged [ASSUMED] for supply-chain trust. The planner MUST gate each new package install behind a `checkpoint:human-verify` task that mirrors the Phase 1 PACKAGE-LEGITIMACY.md process. The human reviewer updates `docs/validation/PACKAGE-LEGITIMACY.md` with a new Phase 2 section before any `uv add` runs.

| Package | Registry | Age / Activity | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|---------------|-----------|-------------|-----------|-------------|
| `fhir.resources` | PyPI | v8.2.0 released 2026-02-02; active | High | github.com/nazrulworld/fhir.resources | N/A [ASSUMED] | Pending PACKAGE-LEGITIMACY review |
| `pymongo` | PyPI | v4.17.0; MongoDB-official | Very high | github.com/mongodb/mongo-python-driver | N/A [ASSUMED] | Pending PACKAGE-LEGITIMACY review |
| `rq` | PyPI | v2.9.1; active | High | github.com/rq/rq | N/A [ASSUMED] | Pending PACKAGE-LEGITIMACY review |
| `hl7apy` | PyPI | v1.3.5 released 2024-03-13; CRS4 | Moderate | github.com/crs4/hl7apy | N/A [ASSUMED] | Pending PACKAGE-LEGITIMACY review |
| `pytesseract` | PyPI | v0.3.13 released 2024-08-16 | High | github.com/madmaze/pytesseract | N/A [ASSUMED] | Pending PACKAGE-LEGITIMACY review |
| `boto3` | PyPI | v1.43.27; AWS-official | Very high | github.com/boto/boto3 | N/A [ASSUMED] | Pending PACKAGE-LEGITIMACY review |
| `openpyxl` | PyPI | v3.1.5 released 2024-06-28; MIT | Very high | foss.heptapod.net/openpyxl/openpyxl | N/A [ASSUMED] | Pending PACKAGE-LEGITIMACY review |
| `pypdf` | PyPI | v6.13.2 released 2024-09-17; active successor to PyPDF2 | High | github.com/py-pdf/pypdf | N/A [ASSUMED] | Pending PACKAGE-LEGITIMACY review |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck unavailable)
**Packages flagged as suspicious [SUS]:** none identified — all packages are from known, official maintainers with established histories. Human review still required per DEC-supply-chain-gate.

**Package-legitimacy checkpoint task:** The plan's Wave 0 MUST include a `checkpoint:human-verify` task. The reviewer confirms each package against PyPI (downloads, source repo, maintainer authenticity), records the verified version, and writes a Phase 2 section in `docs/validation/PACKAGE-LEGITIMACY.md` before any `uv add` runs. This mirrors the Phase 1 process (DEC-supply-chain-gate, T-01-SC/01).

*If slopcheck was unavailable at research time, all packages above are tagged [ASSUMED] and the planner must gate each install behind a `checkpoint:human-verify` task.*

---

## Architecture Patterns

### System Architecture Diagram

```
HTTP POST /ingest/{site_id}
       |
       v
[ingestion-service: FastAPI]
  authn (veridoc-auth) + tenancy (veridoc-tenancy) + RBAC
       |
       v
[SourceProfile registry] --- config: per-site {modality, adapter_type}
       |
       v (enqueue job)
[Redis queue (RQ)] <--- rq worker (forked process)
       |                        |
       |                        v
       |               [SourceAdapter.ingest(payload)]
       |                        |
       |         +--------------+--------------+--------------+
       |         |              |              |              |
       v         v              v              v              v
   native FHIR  HL7 v2.x  PDF/Excel OCR    paper/scanned  proprietary
   adapter      adapter    adapter          adapter        (NotImplemented)
                |
                v (all adapters produce)
         [FHIRBundle: list[FHIRResource]]
                |
                v
         [pseudonym_token] --- veridoc-pseudonym
                |
                v
         [veridoc-fhir.FhirRepository.save()]
                |
                +---> MongoDB: fhir_resources collection (FHIR JSON docs)
                |
                v
         [create Provenance resource] ---> MongoDB
                |
                v
         [BlobStore.put(original_doc)] ---> MinIO / S3 (original retained)
                |
                v
         [append_audit(session, AuditEvent)] ---> Postgres audit_log
                |
                v
         job.result = {resource_ids, provenance_id, ocr_confidence?}
```

The key structural insight: adapters differ, but everything downstream of the FHIR model (Mongo persistence, provenance, pseudonymization, audit) is source-agnostic.

### Recommended Project Structure

```
libs/
  veridoc-fhir/
    src/veridoc_fhir/
      models.py        # FHIR R4B resource type aliases + Meta/extension helpers
      repository.py    # FhirRepository (AsyncMongoClient-backed)
      provenance.py    # create_provenance() factory
      extensions.py    # custom extension URLs (OCR confidence, ALCOA flags)
    tests/
      fixtures/fhir/   # Synthea-generated JSON bundles (committed)
      test_models.py
      test_repository.py

  veridoc-ingestion/
    src/veridoc_ingestion/
      adapter.py         # SourceAdapter ABC + SourceProfile dataclass
      registry.py        # SourceProfileRegistry (YAML/env-driven config)
      adapters/
        native_fhir.py   # NativeFhirAdapter
        hl7v2.py         # HL7v2Adapter (hl7apy + mapping layer)
        pdf_excel.py     # PdfExcelAdapter (pypdf + openpyxl)
        ocr.py           # OcrAdapter (OcrEngine + entity extraction)
        proprietary.py   # ProprietaryAdapter (raises NotImplemented)
      ocr_engine.py      # OcrEngine ABC + TesseractEngine + stub engines
      blob_store.py      # BlobStore ABC + S3BlobStore (boto3, MinIO-compatible)
      mapping/
        hl7v2_fhir.py    # Explicit HL7 v2 segment → FHIR mapping layer
      worker.py          # RQ job function: ingest_job(payload) → calls adapter
    tests/
      fixtures/hl7/      # Hand-crafted ADT_A01 / ORU_R01 test messages
      fixtures/pdf/      # Sample structured PDF fixtures
      fixtures/images/   # Sample scanned-document images (TIFF/PNG)
      test_adapters.py
      test_ocr_engine.py
      test_blob_store.py

services/
  ingestion-service/
    src/ingestion_service/
      config.py          # Settings (pydantic-settings): Mongo URL, Redis URL, blob config
      main.py            # FastAPI app (clone reference-service pattern)
      api/
        ingest.py        # POST /ingest/{site_id}
      worker_main.py     # RQ worker entrypoint: rq worker -u $REDIS_URL ingestion
    migrations/          # (none for Mongo; this covers Postgres audit-only schema deltas if any)
    Dockerfile
    tests/
      test_ingest_api.py
      test_worker_integration.py
```

### Pattern 1: fhir.resources R4B Import and Usage

**CRITICAL:** From v7.0.0 onwards, FHIR R4 (4.0.1) is **gone** from the top-level namespace. The R4B (4.3.0) sub-package is the correct target. Top-level imports (`fhir.resources.patient`) now resolve to FHIR R5.

```python
# Source: github.com/nazrulworld/fhir.resources README.rst [VERIFIED]
# Always use R4B sub-package — never the bare top-level import

from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.medicationrequest import MedicationRequest
from fhir.resources.R4B.adverseevent import AdverseEvent
from fhir.resources.R4B.diagnosticreport import DiagnosticReport
from fhir.resources.R4B.documentreference import DocumentReference
from fhir.resources.R4B.procedure import Procedure
from fhir.resources.R4B.provenance import Provenance

# Construction — dict or keyword args, Pydantic v2 validates on construction
patient = Patient.model_validate({
    "resourceType": "Patient",
    "id": "p-pseudo-abc123",         # pseudonymized ID
    "meta": {
        "source": "urn:veridoc:source:native-fhir:site-001",  # D-03
    },
    "active": True,
    "name": [{"text": "PSEUDONYMIZED"}],  # PII pseudonymized at ingestion (D-14)
    "birthDate": "1985-06-12"
})

# Serialization (Pydantic v2 API — NOT .dict() / .json())
patient_dict = patient.model_dump()
patient_json = patient.model_dump_json()

# Deserialization from JSON string
patient = Patient.model_validate_json(json_str)
```

### Pattern 2: Provenance + meta.source

```python
# Source: hl7.org/fhir/R4B/provenance.html + fhir.resources README [VERIFIED]

from datetime import datetime, timezone
from fhir.resources.R4B.provenance import Provenance

def create_provenance(
    target_ref: str,       # e.g. "Patient/p-pseudo-abc123"
    source: str,           # e.g. "urn:veridoc:source:hl7v2:site-002"
    ingestion_path: str,   # e.g. "hl7v2"
    actor_ref: str,        # e.g. "Device/ingestion-service"
    ocr_confidence: float | None = None,  # None for non-OCR paths
) -> Provenance:
    ext = []
    if ocr_confidence is not None:
        ext.append({
            "url": "urn:veridoc:extension:ocr-confidence",
            "valueDecimal": ocr_confidence,
        })
    ext.append({
        "url": "urn:veridoc:extension:ingestion-path",
        "valueString": ingestion_path,
    })
    return Provenance.model_validate({
        "resourceType": "Provenance",
        "target": [{"reference": target_ref}],
        "recorded": datetime.now(timezone.utc).isoformat(),
        "extension": ext if ext else None,
        "agent": [{"who": {"reference": actor_ref}}],
        "entity": [{"role": "source", "what": {"reference": source}}],
    })
```

### Pattern 3: FhirRepository (pymongo AsyncMongoClient)

```python
# Source: pymongo.readthedocs.io async tutorial [VERIFIED: pymongo 4.17]
# Motor is deprecated (EOL 2026-05-14) — use AsyncMongoClient directly

from pymongo import AsyncMongoClient
from fhir.resources.R4B.patient import Patient

class FhirRepository:
    """Async FHIR resource persistence to MongoDB."""

    def __init__(self, mongo_url: str, db_name: str = "veridoc_fhir") -> None:
        self._client = AsyncMongoClient(mongo_url)
        self._db = self._client[db_name]
        # One collection per resource type (industry pattern; Smile CDR uses same)
        self._col = self._db["fhir_resources"]  # unified with resourceType field indexed

    async def create_indexes(self) -> None:
        """Run once at startup. Create compound indexes for common queries."""
        await self._col.create_index([("resourceType", 1), ("id", 1)], unique=True)
        await self._col.create_index([("resourceType", 1), ("subject.reference", 1)])
        await self._col.create_index([("resourceType", 1), ("meta.source", 1)])
        await self._col.create_index("id")

    async def save(self, resource) -> str:
        """Upsert a fhir.resources model. Returns MongoDB _id."""
        doc = resource.model_dump()
        doc["_resource_type"] = resource.resource_type   # top-level indexed copy
        result = await self._col.replace_one(
            {"resourceType": doc["resourceType"], "id": doc["id"]},
            doc,
            upsert=True,
        )
        return str(result.upserted_id or doc["id"])

    async def find_by_patient(self, patient_id: str, resource_type: str) -> list[dict]:
        """Return all resources of resource_type referencing patient_id."""
        cursor = self._col.find({
            "resourceType": resource_type,
            "subject.reference": f"Patient/{patient_id}",
        })
        return await cursor.to_list(length=None)
```

**Collection design choice:** Single collection `fhir_resources` with `resourceType` indexed (industry pattern from Smile CDR; avoids JOIN anti-pattern in MongoDB; simple compound index `(resourceType, id)` is unique; `(resourceType, subject.reference)` covers patient queries). [ASSUMED: index cardinalities are suitable for fixture-scale; production may need sharding key — defer to Phase 5.]

### Pattern 4: OcrEngine Abstraction (mirroring KMSKeyring)

```python
# Source: pattern derived from libs/veridoc-crypto/kms.py (verified in codebase)
# Mirror exactly: ABC + LocalEngine (Tesseract) + cloud stubs

import abc
from dataclasses import dataclass

@dataclass
class OcrResult:
    text: str
    document_confidence: float    # mean of per-word conf > 0; 0.0–1.0 scale
    word_confidences: list[float] # raw per-word confidence list
    flagged: bool                 # True if document_confidence < 0.95
    escalated: bool               # True if document_confidence < 0.85


class OcrEngine(abc.ABC):
    """Provider-portable OCR abstraction (mirrors KMSKeyring in veridoc-crypto)."""

    @abc.abstractmethod
    def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        """Run OCR on image_bytes; return OcrResult with confidence."""


class TesseractEngine(OcrEngine):
    """Tesseract OCR via pytesseract (D-08). Requires system tesseract-ocr package."""

    def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        import io
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        # image_to_data returns TSV with per-word confidence scores
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        # Filter out empty/whitespace tokens and -1 (block-level non-text entries)
        word_confs = [
            c / 100.0
            for c, txt in zip(data["conf"], data["text"])
            if c != -1 and str(txt).strip()
        ]
        doc_conf = sum(word_confs) / len(word_confs) if word_confs else 0.0
        full_text = " ".join(t for t in data["text"] if str(t).strip())
        return OcrResult(
            text=full_text,
            document_confidence=doc_conf,
            word_confidences=word_confs,
            flagged=doc_conf < 0.95,
            escalated=doc_conf < 0.85,
        )


class TextractEngine(OcrEngine):  # pragma: no cover — DEC-cloud-provider OPEN
    def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        raise NotImplementedError("Wire when DEC-cloud-provider closes to AWS")


class AzureDocumentIntelligenceEngine(OcrEngine):  # pragma: no cover
    def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        raise NotImplementedError("Wire when DEC-cloud-provider closes to Azure")
```

### Pattern 5: BlobStore Abstraction (mirroring KMSKeyring)

```python
# Source: pattern derived from libs/veridoc-crypto/kms.py + boto3 MinIO docs [VERIFIED]

import abc
import boto3

class BlobStore(abc.ABC):
    """Provider-portable blob store (mirrors KMSKeyring; DEC-cloud-provider OPEN)."""

    @abc.abstractmethod
    def put(self, key: str, data: bytes, content_type: str) -> str:
        """Upload bytes; return URL or URI of stored object."""

    @abc.abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve bytes by key."""


class S3BlobStore(BlobStore):
    """S3-compatible blob store. Works with MinIO (endpoint_url) and real S3."""

    def __init__(self, bucket: str, endpoint_url: str | None = None,
                 access_key: str = "", secret_key: str = "") -> None:
        self._bucket = bucket
        kwargs: dict = {}
        if endpoint_url:  # MinIO local/CI path
            kwargs["endpoint_url"] = endpoint_url
        if access_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key
        self._client = boto3.client("s3", **kwargs)

    def put(self, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(Bucket=self._bucket, Key=key,
                                 Body=data, ContentType=content_type)
        return f"s3://{self._bucket}/{key}"

    def get(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()
```

MinIO local/CI config: `endpoint_url="http://minio:9000"`, credentials from env (same K8s Secret pattern as Phase 1). No code change needed to switch to real S3 — just remove `endpoint_url`.

### Pattern 6: SourceAdapter + SourceProfile

```python
# Claude's Discretion choice — concrete recommendation

from dataclasses import dataclass
import abc
from enum import StrEnum

class SourceModality(StrEnum):
    NATIVE_FHIR = "native-fhir"
    HL7V2 = "hl7v2"
    PDF_EXCEL = "pdf-excel"
    OCR = "ocr"
    PROPRIETARY = "proprietary"   # raises NotImplemented


@dataclass(frozen=True)
class SourceProfile:
    site_id: str
    modality: SourceModality
    config: dict  # adapter-specific config (e.g. FHIR server URL, HL7 version)


class SourceAdapter(abc.ABC):
    """Single ingestion interface; N implementations per D-05."""

    @abc.abstractmethod
    def ingest(self, payload: bytes, profile: SourceProfile) -> list:
        """Parse payload; return list of fhir.resources.R4B model instances.

        The returned list MUST include at least one resource for each success
        criterion resource type applicable to the modality.
        """
```

### Pattern 7: RQ Job with Audit/Provenance Writes

```python
# Source: python-rq.org/docs + github.com/rq/rq [VERIFIED]
# Key: RQ workers run in forked processes — no shared FastAPI app state.
# Each job must open its OWN Postgres session for append_audit.
# JSONSerializer is mandatory (no pickle — security requirement).

from rq import Queue
from rq.serializers import JSONSerializer
from redis import Redis

def make_queue(redis_url: str) -> Queue:
    return Queue(
        "ingestion",
        connection=Redis.from_url(redis_url),
        serializer=JSONSerializer,  # REQUIRED: no pickle
    )


# Worker function (in veridoc_ingestion/worker.py)
def ingest_job(
    site_id: str,
    modality: str,
    payload_key: str,   # blob store key (not raw bytes — JSON-serializable)
    tenant_id: str,
    actor_id: str,
) -> dict:
    """RQ job function. Runs in a forked worker process.

    Opens its own DB + Mongo sessions. Calls append_audit for the ingest event.
    Returns dict with resource IDs for result tracking.
    """
    from veridoc_ingestion.registry import get_adapter
    from veridoc_fhir.repository import FhirRepository
    from veridoc_audit.sdk import append_audit
    from veridoc_audit.models import AuditEvent
    # ... implementation
```

**Audit boundary in async jobs:** The Phase 1 pattern (`append_audit` joins the caller's transaction, no commit) does NOT work in RQ workers because workers have no shared SQLAlchemy session. Workers MUST:
1. Open a new `Session` via `session_scope(factory)`.
2. Call `append_audit(session, event)` — which still uses `pg_advisory_xact_lock`.
3. Commit the session at the end of the job (the audit write IS the commit here).

This is the deliberate D-06 deviation from Phase 1's synchronous-audit default.

### Pattern 8: HL7 v2.x → FHIR Mapping Layer

```python
# Source: crs4.github.io/hl7apy/tutorial [VERIFIED] + hl7.org/fhir/uv/v2mappings [CITED]

from hl7apy.parser import parse_message
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.encounter import Encounter

def map_adt_a01_to_fhir(hl7_msg_str: str) -> list:
    """Map ADT_A01 → [Patient, Encounter, optional Condition/Procedure].
    Follows official HL7 v2-to-FHIR ConceptMap (hl7.org/fhir/uv/v2mappings).
    """
    msg = parse_message(hl7_msg_str)

    # PID.5 → Patient.name (pseudonymized at ingestion; only used as input)
    # PID.3 → Patient.identifier (used to derive pseudonym_token)
    # PID.7 → Patient.birthDate
    patient_id = msg.pid.pid_3.value  # internal patient ID
    # ... derive pseudonym_token(patient_id, pid_3) via veridoc-pseudonym

    # PV1 → Encounter
    # PV1.2 codes: E→EMER, I→IMP, O→AMB, P→PRENC (official v2-to-FHIR mapping)
    class_map = {"E": "EMER", "I": "IMP", "O": "AMB", "P": "PRENC"}
    encounter_class = class_map.get(msg.pv1.pv1_2.value, "AMB")
    # ...
```

**HL7 v2 → FHIR segment mapping table** (official HL7 ConceptMap, hl7.org/fhir/uv/v2mappings):

| HL7 v2 Segment | FHIR R4B Resource | Key Fields |
|---|---|---|
| MSH | MessageHeader, Provenance | Sender, receiver, timestamp |
| PID | Patient | Name (pseudonymized), DOB, identifiers |
| PV1 | Encounter | Class (E/I/O/P → EMER/IMP/AMB/PRENC), admission date |
| EVN | Provenance | Event type, recorded datetime |
| OBX | Observation | LOINC code (OBX-3), value (OBX-5), units (OBX-6) |
| DG1 | Condition | Diagnosis code (ICD-10), onset date |
| PR1 | Procedure | Procedure code, date |
| AL1 | AllergyIntolerance | (not in phase's 9 required resources; emit if present) |

**ORU_R01 mapping** (lab results): OBX segments → Observation; OBR → DiagnosticReport (OBR-4 → DiagnosticReport.code LOINC).

### Pattern 9: DocumentReference with OCR Confidence (D-09)

```python
# Source: hl7.org/fhir/R4B/documentreference.html [CITED]

from fhir.resources.R4B.documentreference import DocumentReference

def build_document_reference(
    blob_uri: str,           # e.g. "s3://veridoc-docs/site-001/scan-001.tiff"
    patient_ref: str,        # pseudonymized patient reference
    ocr_confidence: float,   # 0.0–1.0
    mime_type: str = "image/tiff",
    site_id: str = "",
) -> DocumentReference:
    """Build a FHIR DocumentReference for a scanned document. D-09."""
    flags = []
    if ocr_confidence < 0.95:
        flags.append("legibility-flag")    # ALCOA+ Legible principle flag
    if ocr_confidence < 0.85:
        flags.append("legibility-escalate")  # escalate to human

    return DocumentReference.model_validate({
        "resourceType": "DocumentReference",
        "status": "current",
        "docStatus": "preliminary",        # pending legibility review
        "subject": {"reference": patient_ref},
        "content": [{
            "attachment": {
                "contentType": mime_type,
                "url": blob_uri,           # points to retained original (ALCOA+ Original)
            }
        }],
        "meta": {
            "source": f"urn:veridoc:source:ocr:{site_id}",
        },
        "extension": [
            {
                "url": "urn:veridoc:extension:ocr-confidence",
                "valueDecimal": round(ocr_confidence, 4),
            },
            *(
                [{"url": "urn:veridoc:extension:alcoa-legibility-flag", "valueString": f}]
                for f in flags
            ),
        ],
    })
```

### Anti-Patterns to Avoid

- **Top-level fhir.resources import for R4:** `from fhir.resources.patient import Patient` now imports FHIR R5. Always use `from fhir.resources.R4B.patient import Patient`.
- **Motor driver:** Motor is EOL (deprecated 2026-05-14). Do not add it. Use `pymongo.AsyncMongoClient`.
- **Pickle serialization in RQ:** Default RQ serialization is pickle and is vulnerable to RCE. Always pass `serializer=JSONSerializer` to `Queue()`.
- **Synchronous `append_audit` with the Phase 1 same-txn pattern in RQ workers:** Workers run in forked processes with no shared session. Each job must open its own Session and commit after calling `append_audit`.
- **Raw bytes in RQ jobs:** JSON serializer can only handle primitives. Pass blob store keys (strings) into jobs, not raw document bytes.
- **Motor:** Deprecated. Never install.
- **Hand-rolling HL7 v2 parsing:** hl7apy covers v2.1–2.8.2 with structured field access; do not parse ER7-encoded strings manually.
- **Single FHIR pseudo-key per collection with no resourceType index:** Mongo queries on an unindexed `resourceType` field scan the entire collection. Always compound-index `(resourceType, id)` at startup.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FHIR R4B resource validation | Custom Pydantic models for 9 resources | `fhir.resources` R4B | 100+ resource types with nested validation; spec changes require tracking |
| HL7 v2.x segment parsing | Custom ER7 string parser | `hl7apy` | HL7 has 2.8+ versions, optional components, repetitions, escape sequences |
| OCR confidence extraction | Custom Tesseract subprocess call | `pytesseract.image_to_data()` | TSV output with per-word confidence is the correct API; subprocess management is fragile |
| S3/MinIO object storage | Custom HTTP client for blob storage | `boto3` | Auth, multipart, error handling, retry logic; S3 API has 40+ edge cases |
| Excel/PDF parsing | Custom binary readers | `openpyxl` / `pypdf` | Format complexity; do not hand-roll |
| FHIR R4B meta.source | Custom sidecar table for provenance | FHIR `Provenance` resource + `meta.source` | Spec-native; downstream agents (Phases 4–6) read standard FHIR provenance |

**Key insight:** The FHIR spec is 3,000+ pages. `fhir.resources` embeds all of it as Pydantic v2 validators. Any hand-rolled model will silently accept invalid FHIR.

---

## Common Pitfalls

### Pitfall 1: fhir.resources v7+ dropped FHIR R4 top-level
**What goes wrong:** `from fhir.resources.patient import Patient` silently imports the FHIR R5 Patient resource. R5 has different cardinalities and field names. Tests may pass while silently writing R5 documents.
**Why it happens:** v7.0.0 changelog note: "From version 7.0.0; there is no FHIR R4 instead of R4B is available as sub-package." Upstream docs are sparse on this.
**How to avoid:** Use `from fhir.resources.R4B.<module> import <Class>` throughout. Add a module-level `__all__` in `veridoc_fhir/models.py` that re-exports only R4B classes.
**Warning signs:** Resources serializing with fields not present in R4 (e.g., `R5`-only fields appearing in output).

### Pitfall 2: Motor is deprecated — do not install
**What goes wrong:** Installing `motor` brings in a package that will receive no security fixes after May 2026.
**Why it happens:** motor is still the top result for "async MongoDB Python".
**How to avoid:** Use `pymongo>=4.13` `AsyncMongoClient`. Both have identical async APIs.
**Warning signs:** A `motor` dependency in `pyproject.toml`.

### Pitfall 3: RQ default pickle serializer is an RCE vector
**What goes wrong:** Anyone with Redis write access can enqueue a job with malicious pickled data, executing arbitrary code in the worker.
**Why it happens:** RQ defaults to `pickle` for backward compatibility.
**How to avoid:** Pass `serializer=JSONSerializer` to every `Queue()` constructor. Enforce in `rq worker` CLI: `rq worker --serializer rq.serializers.JSONSerializer`.
**Warning signs:** `Queue(connection=redis)` without `serializer=` argument.

### Pitfall 4: Phase 1 same-transaction audit pattern doesn't work in RQ workers
**What goes wrong:** `append_audit` calls `pg_advisory_xact_lock` inside the caller's transaction. In a forked RQ worker, there is no caller transaction — the session is closed. The advisory lock prevents any audit write.
**Why it happens:** The Phase 1 pattern relies on the FastAPI request's SQLAlchemy session staying open across the handler. Workers are isolated processes.
**How to avoid:** Workers open their own `Session`, call `append_audit(session, event)`, then commit explicitly. The advisory lock still prevents chain forks because it's process-level, not thread-level.
**Warning signs:** `TxnNotFoundError` or `InvalidRequestError` from SQLAlchemy in worker logs.

### Pitfall 5: R4B AdverseEvent has a DIFFERENT structure than R4 AdverseEvent
**What goes wrong:** The HL7 FHIR v2-to-FHIR mapping guide targets R4 (4.0.1). AdverseEvent in R4B had no structural changes, but if you inadvertently use an R5-era AdverseEvent reference, the `seriousness` cardinality changed.
**Why it happens:** Mix-up between R4, R4B, and R5 in search results / documentation.
**How to avoid:** Always verify imports against `fhir.resources.R4B`. DiagnosticReport and Observation in R4B have additional reference targets but no breaking changes.
**Warning signs:** Validation errors on `AdverseEvent.seriousness` or `suspectEntity`.

### Pitfall 6: MongoDB indexes must be created at startup
**What goes wrong:** Without compound indexes on `(resourceType, id)` and `(resourceType, subject.reference)`, FHIR resource queries perform full collection scans.
**Why it happens:** MongoDB is schemaless; indexes are not auto-created.
**How to avoid:** Call `await repository.create_indexes()` in the FastAPI `lifespan` startup hook. Guard with `create_index(..., unique=True)` for `(resourceType, id)`.
**Warning signs:** Slow queries; `explain()` shows `COLLSCAN`.

### Pitfall 7: Synthea output includes R4 US Core IG extensions by default when use_us_core_ig=true
**What goes wrong:** Some Synthea output fields (e.g., `us-core-race` extension) use profiles not in base R4B. `fhir.resources.R4B` validation may reject unknown extensions depending on model config.
**Why it happens:** Synthea defaults to `use_us_core_ig = false`; CI scripts may set it differently.
**How to avoid:** Generate Synthea fixtures with `exporter.fhir.use_us_core_ig = false`. Use `Patient.model_validate(data)` with `model_config = ConfigDict(extra="allow")` in the test fixtures only.
**Warning signs:** Pydantic `ValidationError` on Synthea-generated bundles in tests.

### Pitfall 8: Tesseract not available in the Docker image
**What goes wrong:** `pytesseract` raises `TesseractNotFoundError` at runtime if the `tesseract` binary is not on `PATH`.
**Why it happens:** pytesseract is a Python wrapper; the system Tesseract binary must be installed separately.
**How to avoid:** Add to Dockerfile: `RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-eng`. CI: same apt install step in the GitHub Actions workflow.
**Warning signs:** `TesseractNotFoundError` or `FileNotFoundError: tesseract` in logs.

### Pitfall 9: Provenance.recorded must be a timezone-aware ISO 8601 datetime
**What goes wrong:** Passing a naive `datetime.now()` without UTC timezone raises Pydantic validation errors in `fhir.resources.R4B`.
**Why it happens:** FHIR `instant` type requires timezone offset.
**How to avoid:** Always use `datetime.now(timezone.utc).isoformat()` for `recorded`.

---

## Code Examples

### OCR confidence computation from pytesseract

```python
# Source: pytesseract PyPI documentation + nanonets.com OCR tutorial [CITED]

import pytesseract
from PIL import Image
import io

def compute_ocr_confidence(image_bytes: bytes) -> tuple[str, float, list[float]]:
    """Returns (text, document_confidence 0-1, per_word_confidences)."""
    image = Image.open(io.BytesIO(image_bytes))
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    word_confs = []
    words = []
    for conf, txt in zip(data["conf"], data["text"]):
        if conf != -1 and str(txt).strip():   # -1 = block/para/line level entry
            word_confs.append(conf / 100.0)   # Tesseract returns 0-100
            words.append(txt)

    doc_conf = sum(word_confs) / len(word_confs) if word_confs else 0.0
    return " ".join(words), doc_conf, word_confs
```

### Synthea fixture generation for CI

```bash
# Source: github.com/synthetichealth/synthea/wiki/HL7-FHIR [VERIFIED]
# Java 21 is available on this machine (verified: openjdk 21.0.11)

# Download once; check into scripts/ or Makefile
wget https://github.com/synthetichealth/synthea/releases/latest/download/synthea-with-dependencies.jar

# Generate 10 reproducible patients in FHIR R4B JSON format
# -s seed ensures reproducibility across CI runs
java -jar synthea-with-dependencies.jar \
  -p 10 \
  -s 42 \
  --exporter.fhir.export=true \
  --exporter.fhir.use_us_core_ig=false \
  --exporter.baseDirectory=./output

# Output: ./output/fhir/*.json (one transaction Bundle per patient)
# Commit fixture bundles to libs/veridoc-fhir/tests/fixtures/fhir/
```

### RQ worker enqueue with JSONSerializer

```python
# Source: python-rq.org/docs [VERIFIED]

from redis import Redis
from rq import Queue
from rq.serializers import JSONSerializer

redis = Redis.from_url(settings.redis_url)
q = Queue("ingestion", connection=redis, serializer=JSONSerializer)

# Enqueue (only JSON-serializable args)
job = q.enqueue(
    "veridoc_ingestion.worker.ingest_job",
    site_id=site_id,
    modality=modality.value,
    payload_key=blob_key,   # string reference to blob store
    tenant_id=tenant_id,
    actor_id=actor_id,
    on_success=audit_success_callback,
    on_failure=audit_failure_callback,
    job_timeout=300,        # 5 min OCR timeout
    result_ttl=3600,        # keep result 1 hour
)

# Worker process start command
# rq worker ingestion --serializer rq.serializers.JSONSerializer --url $REDIS_URL
```

### MongoDB lifespan startup (FastAPI)

```python
# Source: mongodb.com/developer/python/python-quickstart-fastapi [CITED]
from contextlib import asynccontextmanager
from fastapi import FastAPI
from veridoc_fhir.repository import FhirRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = FhirRepository(mongo_url=settings.mongodb_url)
    await repo.create_indexes()
    app.state.fhir_repo = repo
    yield
    repo._client.close()

app = FastAPI(lifespan=lifespan)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `motor` for async MongoDB with Python | `pymongo.AsyncMongoClient` | motor deprecated 2025-05-14 | Do not install motor; pymongo 4.13+ is the answer |
| `fhir.resources.patient` imports R4 | `fhir.resources.R4B.patient` imports R4B (4.3.0) | v7.0.0 (2023) | Always use R4B sub-package |
| Pickle serialization in RQ | `JSONSerializer` (built into RQ) | RQ 1.x+ | Security: JSON-only eliminates pickle RCE vector |
| PyPDF2 (archived) | `pypdf` (active fork) | 2022 | Use `pypdf`, not `PyPDF2` |

**Deprecated / outdated:**
- `motor`: deprecated May 2026; no security patches after EOL.
- `python-hl7` (PyPI: `hl7`): last release March 2022; use `hl7apy` instead.
- `fhir.resources` top-level R4 imports: gone since v7.0.0; now resolves to R5.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `fhir.resources` R4B sub-package is equivalent to R4 (4.0.1) for all 9 phase-required resource types | Standard Stack, Code Examples | If DiagnosticReport or Observation R4B changes break agent consumers in Phase 5, minor refactor needed; low risk given HL7 confirmed "no structural changes" |
| A2 | MongoDB single collection `fhir_resources` with compound indexes is sufficient at fixture scale | Architecture Patterns (repository) | If collection grows beyond 10M docs, sharding strategy needed; deferred to Phase 5 scale |
| A3 | `rq.serializers.JSONSerializer` is sufficient for all job payloads (primitive types only in job args) | Architecture Patterns (RQ) | If complex objects must be passed between steps, switch to arq or serialize to blob first |
| A4 | All 8 new packages will pass PACKAGE-LEGITIMACY.md human review | Package Legitimacy Audit | If any package is rejected, a substitute must be chosen; this research has identified the most legitimate candidates |
| A5 | Java 21 (verified present) is sufficient to run Synthea JAR | Environment Availability | If Synthea requires Java 17+ specifically, Java 21 satisfies it |
| A6 | Tesseract apt package `tesseract-ocr` 5.3.4 is available in Ubuntu 24.04 base image | Environment Availability (Docker) | If base image is Alpine, use `apk add tesseract-ocr` instead |
| A7 | Synthea generates all 9 required FHIR resources including AdverseEvent in default output | Code Examples | Synthea by default emits Patient, Encounter, Observation, Condition, MedicationRequest, DiagnosticReport, Procedure, DocumentReference. AdverseEvent may require specific module configuration — hand-crafted edge cases cover this gap |

---

## Open Questions

1. **Does Synthea emit AdverseEvent resources by default?**
   - What we know: Synthea emits Patient, Encounter, Observation, Condition, MedicationRequest, DiagnosticReport, Procedure. DocumentReference is emitted with US Core IG enabled.
   - What's unclear: AdverseEvent may not be in Synthea's default output for all patient profiles.
   - Recommendation: Use Synthea for the 8 resources it reliably emits; hand-craft `AdverseEvent` fixture JSON for the 9th resource (straightforward with `fhir.resources.R4B.adverseevent.AdverseEvent`).

2. **Should `DocumentReference.docStatus` be `preliminary` or `final` after OCR?**
   - What we know: FHIR R4B `docStatus` values are `preliminary | final | amended | entered-in-error`. OCR output is inherently uncertain.
   - What's unclear: The OCR path produces a preliminary result pending ALCOA+ legibility review (Phase 5).
   - Recommendation: Set `docStatus = "preliminary"` at ingestion time; ALCOA+ agent (Phase 5) updates to `final` or escalates.

3. **Does `veridoc-pseudonym.pseudonym_token` accept any `natural_id` string?**
   - What we know: `pseudonym_token(patient_id, natural_id)` computes `HMAC-SHA256(per_patient_key, natural_id)`. Any string is valid.
   - What's unclear: For HL7 v2 PID.3 (CX-encoded identifier with assigning authority), the format is `ID^^^Authority^MR`. Should the whole CX string be used or just the ID portion?
   - Recommendation: Use the raw ID component (PID.3.1) stripped of assigning authority as `natural_id`. Document the choice in `veridoc-ingestion/mapping/hl7v2_fhir.py`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Java 21 | Synthea JAR execution | ✓ | OpenJDK 21.0.11 | — |
| Python 3.12 | All libs/services | ✓ | 3.12.3 | — |
| uv | Package management | ✓ | 0.11.20 | — |
| Redis CLI | RQ queue verification | ✓ | 7.0.15 | — |
| Docker | MongoDB + MinIO containers (CI) | ✗ | — | Use `testcontainers` with host Docker socket in CI |
| Tesseract binary | `pytesseract.TesseractEngine` | ✗ (dev machine) | — | Install via `apt-get install tesseract-ocr` in Dockerfile and CI |
| MongoDB (mongod) | `FhirRepository` integration tests | ✗ (dev machine) | — | `testcontainers[mongo]` in tests; Helm StatefulSet in cluster |
| MinIO | Blob store integration tests | ✗ (dev machine) | — | `testcontainers[minio]` in tests; Helm StatefulSet in cluster |

**Missing dependencies with no fallback:** None — all missing dependencies have testcontainers or Helm-based fallbacks.

**Missing dependencies with fallback:**
- Tesseract: Dockerfile + CI apt-install; TesseractEngine skipped in unit tests via `pytest.importorskip("pytesseract")` guard.
- MongoDB: `testcontainers` for integration tests; can be mocked with `unittest.mock.AsyncMock` for unit tests.
- MinIO: `testcontainers[minio]` for integration tests; boto3 client can use `moto` mock for unit tests.
- Docker: GitHub Actions provides Docker. Local dev can use Colima or Docker Desktop.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already APPROVED, workspace dev dependency) |
| Config file | `/home/emoadm/projects/veridoc/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest libs/veridoc-fhir libs/veridoc-ingestion -x -q --import-mode=importlib` |
| Full suite command | `pytest libs/ services/ -x -q --import-mode=importlib` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EMR-01-SC1 | Synthea FHIR R4B data loads into all 9 resource types and is queryable | Integration | `pytest libs/veridoc-fhir/tests/test_repository.py -x` | ❌ Wave 0 |
| EMR-01-SC2a | HL7 v2.x ADT_A01 normalizes to Patient + Encounter FHIR resources | Unit | `pytest libs/veridoc-ingestion/tests/test_adapters.py::test_hl7v2_adt -x` | ❌ Wave 0 |
| EMR-01-SC2b | Structured PDF/Excel input normalizes to same FHIR R4B model as HL7 path | Unit | `pytest libs/veridoc-ingestion/tests/test_adapters.py::test_pdf_excel -x` | ❌ Wave 0 |
| EMR-01-SC3 | Scanned image produces DocumentReference with OCR confidence score | Unit | `pytest libs/veridoc-ingestion/tests/test_ocr_engine.py -x` | ❌ Wave 0 |
| EMR-01-SC3b | OCR confidence < 0.95 sets legibility-flag extension; < 0.85 sets legibility-escalate | Unit | `pytest libs/veridoc-ingestion/tests/test_adapters.py::test_ocr_flags -x` | ❌ Wave 0 |
| EMR-01-SC4 | Patient-identifiable fields pseudonymized at ingestion; same patient → same token across sources | Unit | `pytest libs/veridoc-ingestion/tests/test_adapters.py::test_pseudonymization -x` | ❌ Wave 0 |
| EMR-01-prov | Every ingested resource has a Provenance resource with meta.source set | Unit | `pytest libs/veridoc-fhir/tests/test_provenance.py -x` | ❌ Wave 0 |
| EMR-01-audit | Every ingest job writes an audit event through veridoc-audit | Integration | `pytest services/ingestion-service/tests/test_worker_integration.py -x` | ❌ Wave 0 |
| EMR-01-queue | RQ job enqueue → worker picks up → FHIR resources appear in MongoDB | Integration | `pytest services/ingestion-service/tests/test_ingest_api.py -x` | ❌ Wave 0 |
| EMR-01-native | Native FHIR R4B bundle from Synthea round-trips through adapter unchanged | Unit | `pytest libs/veridoc-ingestion/tests/test_adapters.py::test_native_fhir -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest libs/veridoc-fhir libs/veridoc-ingestion -x -q`
- **Per wave merge:** `pytest libs/ services/ -x -q`
- **Phase gate:** Full suite green (including integration tests with testcontainers) before `/gsd:verify-work`

### Wave 0 Gaps

All test files are new (no pre-existing veridoc-fhir or veridoc-ingestion libs exist yet).

- [ ] `libs/veridoc-fhir/tests/test_models.py` — covers R4B import + construct + serialize for all 9 resources
- [ ] `libs/veridoc-fhir/tests/test_repository.py` — covers save + find_by_patient (requires testcontainers MongoDB)
- [ ] `libs/veridoc-fhir/tests/test_provenance.py` — covers create_provenance() factory
- [ ] `libs/veridoc-fhir/tests/conftest.py` — shared MongoDB testcontainers fixture
- [ ] `libs/veridoc-ingestion/tests/test_ocr_engine.py` — covers TesseractEngine.extract() + confidence thresholds
- [ ] `libs/veridoc-ingestion/tests/test_adapters.py` — covers all 4 adapter paths
- [ ] `libs/veridoc-ingestion/tests/test_blob_store.py` — covers S3BlobStore with MinIO testcontainer
- [ ] `libs/veridoc-ingestion/tests/conftest.py` — shared MinIO testcontainer fixture
- [ ] `services/ingestion-service/tests/test_ingest_api.py` — HTTP POST /ingest/{site_id}
- [ ] `services/ingestion-service/tests/test_worker_integration.py` — RQ job end-to-end
- [ ] `libs/veridoc-fhir/tests/fixtures/fhir/` — Synthea-generated JSON bundles (committed)
- [ ] `libs/veridoc-ingestion/tests/fixtures/hl7/` — ADT_A01 + ORU_R01 hand-crafted fixtures
- [ ] `libs/veridoc-ingestion/tests/fixtures/pdf/` — sample structured PDF fixture
- [ ] `libs/veridoc-ingestion/tests/fixtures/images/` — sample scanned TIFF/PNG fixture
- [ ] Framework install: already present (pytest in workspace dev deps)

---

## Deployment Delta

**What Phase 2 adds to `deploy/helm/veridoc/` vs Phase 1 baseline:**

New Helm templates needed:
- `templates/mongodb.yaml` — MongoDB StatefulSet (single-node, emptyDir in CI, PVC in prod)
- `templates/minio.yaml` — MinIO StatefulSet (single-node, emptyDir in CI, PVC in prod)
- `templates/ingestion-service.yaml` — Deployment + Service (clone reference-service.yaml pattern)

New `values.yaml` sections:

```yaml
mongodb:
  enabled: true
  image:
    repository: mongo
    tag: "7-jammy"        # MongoDB 7.x; Jammy = Ubuntu 22.04 base
  replicas: 1
  port: 27017
  database: veridoc_fhir
  persistence:
    enabled: false        # emptyDir in kind/CI; PVC with StorageClass in prod
    size: 5Gi

minio:
  enabled: true
  image:
    repository: minio/minio
    tag: "latest"         # Pin to digest in prod
  replicas: 1
  port: 9000
  consolePort: 9001
  defaultBucket: veridoc-docs
  persistence:
    enabled: false

ingestionService:
  enabled: true
  image:
    repository: veridoc/ingestion-service
    tag: "ci"
  replicas: 1
  port: 8000
  healthPath: /healthz
  config:
    mongodbUrl: "mongodb://veridoc-mongodb:27017/veridoc_fhir"
    redisUrl: "redis://veridoc-redis:6379/0"
    blobEndpointUrl: "http://veridoc-minio:9000"
    blobBucket: "veridoc-docs"
```

New secrets in `secrets.yaml`:
- `veridoc-mongodb` (MONGO_INITDB_ROOT_USERNAME, MONGO_INITDB_ROOT_PASSWORD)
- `veridoc-minio` (MINIO_ROOT_USER, MINIO_ROOT_PASSWORD)

**Terraform delta (`deploy/terraform/main.tf`):** Add MongoDB Atlas or Azure CosmosDB (MongoDB API) placeholder when `DEC-cloud-provider` closes; for now, the Helm StatefulSet is the canonical deployment. No Terraform changes needed for the `kind`/CI path.

**GitHub Actions CI delta:** Add `mongod` not needed — testcontainers pulls MongoDB image in tests. The kind cluster CI job (plan 01-06 pattern) adds `minio.yaml` + `mongodb.yaml` to the `helm install` and adds a smoke test that POSTs to `/ingest/{site_id}` and verifies a FHIR resource appears in MongoDB.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (inherited from Phase 1) | Keycloak JWT / RS256 / MFA (already implemented) |
| V3 Session Management | yes (inherited) | Redis session store (already implemented) |
| V4 Access Control | yes | `require_role` on `/ingest` endpoint; deny-by-default |
| V5 Input Validation | yes | `fhir.resources.R4B` Pydantic v2 full-spec validation on all FHIR input |
| V6 Cryptography | yes | Pseudonymization (HMAC-SHA256 via veridoc-pseudonym); envelope encryption for PII (veridoc-crypto); AES-256-GCM at rest |
| V7 Error Handling | yes | Job failure callbacks write audit events; no PII in error messages |
| V10 Malicious Code | yes (supply chain) | DEC-supply-chain-gate: all new packages vetted via PACKAGE-LEGITIMACY.md before install |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pickle RCE via RQ job queue | Tampering/Elevation | `rq.serializers.JSONSerializer` — no pickle |
| Unvalidated FHIR JSON stored to MongoDB | Tampering | `fhir.resources.R4B` Pydantic v2 validation before any persistence |
| PII in MongoDB documents | Information Disclosure | Pseudonymize all Patient identifiers via `veridoc-pseudonym` before `FhirRepository.save()` |
| MongoDB exposed without auth | Information Disclosure | K8s Secret + MONGO_INITDB_ROOT credentials; no unauthenticated access in cluster |
| Blob store object enumeration | Information Disclosure | S3 bucket policy: no public access; access via authenticated client only; keys are non-guessable (UUID + site_id) |
| OCR confidence bypass | Tampering | ALCOA+ flags computed server-side from raw `pytesseract` output; not user-supplied |
| Malicious document upload (OCR path) | Tampering | Document bytes stored to blob store, not executed; PIL/pytesseract only reads image data |
| GDPR Art. 9 — PHI at rest in MongoDB | Information Disclosure | Patient PII fields pseudonymized (name, dob, identifiers) before storage; only pseudonymized tokens appear in FHIR JSON |

**GDPR Art. 9 at ingestion (binding):** Every adapter MUST call `pseudonym_token(patient_id, natural_id)` and replace all PII fields with the pseudonymized token before calling `FhirRepository.save()`. The `patient_id` used for the pseudonym derivation must be consistent across all sources for the same patient (this is the SDV matching precondition for Phase 5). PII fields NOT included in the FHIR model should not be persisted anywhere except the encrypted Postgres `pii_ciphertext` column (Phase 1 pattern).

---

## Sources

### Primary (HIGH confidence)

- `https://github.com/nazrulworld/fhir.resources` — README.rst R4B import paths, Pydantic v2 API, version history [VERIFIED]
- `https://pypi.org/pypi/fhir.resources/json` — version 8.2.0, release date 2026-02-02 [VERIFIED]
- `https://pypi.org/pypi/pymongo/json` — version 4.17.0, MongoDB-official [VERIFIED]
- `https://pypi.org/pypi/motor/json` — version 3.7.1, deprecation date 2026-05-14 [VERIFIED]
- `https://pypi.org/pypi/rq/json` — version 2.9.1, source github.com/rq/rq [VERIFIED]
- `https://pypi.org/pypi/hl7apy/json` — version 1.3.5 (2024-03-13), CRS4 [VERIFIED]
- `https://pypi.org/pypi/pytesseract/json` — version 0.3.13 (2024-08-16) [VERIFIED]
- `https://pypi.org/pypi/boto3/json` — version 1.43.27, AWS-official [VERIFIED]
- `https://pypi.org/pypi/openpyxl/json` — version 3.1.5 (2024-06-28) [VERIFIED]
- `https://pypi.org/pypi/pypdf/json` — version 6.13.2, py-pdf/pypdf [VERIFIED]
- `https://www.hl7.org/fhir/R4B/diff.html` — R4 vs R4B diff: 7 of 9 resources unchanged [VERIFIED]
- `https://crs4.github.io/hl7apy/tutorial/` — hl7apy parsing + construction patterns [CITED]
- `https://www.hl7.org/fhir/R4B/provenance.html` — Provenance required fields [CITED]
- `https://www.hl7.org/fhir/R4B/documentreference.html` — DocumentReference fields + extension pattern [CITED]
- `https://python-rq.org/docs/` — RQ job patterns, JSONSerializer, callbacks [CITED]
- `https://www.hl7.org/fhir/uv/v2mappings/2020Sep/ConceptMap-message-adt-a01-to-bundle.html` — Official ADT_A01 → FHIR mapping [CITED]
- `https://github.com/synthetichealth/synthea/wiki/HL7-FHIR` — Synthea FHIR R4 output format, CLI flags [CITED]
- `libs/veridoc-crypto/src/veridoc_crypto/kms.py` — KMSKeyring abstraction pattern (OcrEngine + BlobStore mirror this) [VERIFIED: codebase]
- `libs/veridoc-audit/src/veridoc_audit/sdk.py` — `append_audit` same-txn pattern; async audit boundary [VERIFIED: codebase]
- `libs/veridoc-pseudonym/src/veridoc_pseudonym/pseudonym.py` — `pseudonym_token` API [VERIFIED: codebase]

### Secondary (MEDIUM confidence)

- `https://pymongo.readthedocs.io/en/4.9.2/async-tutorial.html` — AsyncMongoClient stable since 4.13 [CITED]
- `https://smilecdr.com/docs/fhir_storage_mongodb/fhir_storage_mongodb_module.html` — collection-per-resource-type industry pattern [CITED]
- `https://generalistprogrammer.com/comparisons/celery-vs-rq` — RQ vs Celery throughput comparison 2025 [CITED]

### Tertiary (LOW confidence)

- Multiple WebSearch results confirming general patterns; all cross-verified against primary sources above before being included.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all packages verified against PyPI with version + maintainer
- Architecture (KMS mirror pattern, RQ with JSONSerializer, pymongo AsyncMongoClient): HIGH — all verified against official docs and existing codebase
- fhir.resources R4B: HIGH — verified against README + PyPI + HL7 spec
- Pitfalls: HIGH — pitfalls 1-4 verified directly; pitfalls 5-9 are well-established
- HL7 segment mappings: MEDIUM — official ConceptMap cited; test fixtures will exercise real segments
- Mongo index design: MEDIUM — Smile CDR pattern cited; validate with explain() in tests
- Deployment delta (Helm structure): MEDIUM — based on Phase 1 Helm chart pattern, not tested yet

**Research date:** 2026-06-11
**Valid until:** 2026-09-11 (stable domain; fhir.resources releases infrequently; RQ/pymongo are stable)
