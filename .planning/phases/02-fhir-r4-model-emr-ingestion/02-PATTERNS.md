# Phase 2: FHIR R4 Model & EMR Ingestion - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 34 new/modified files
**Analogs found:** 34 / 34

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `libs/veridoc-fhir/pyproject.toml` | config | — | `libs/veridoc-crypto/pyproject.toml` | exact |
| `libs/veridoc-fhir/src/veridoc_fhir/__init__.py` | config | — | `libs/veridoc-audit/src/veridoc_audit/__init__.py` | exact |
| `libs/veridoc-fhir/src/veridoc_fhir/models.py` | model | transform | `libs/veridoc-audit/src/veridoc_audit/models.py` | role-match |
| `libs/veridoc-fhir/src/veridoc_fhir/repository.py` | service | CRUD | `services/reference-service/src/reference_service/db.py` | partial |
| `libs/veridoc-fhir/src/veridoc_fhir/provenance.py` | utility | transform | `services/reference-service/src/reference_service/api/subjects.py` | partial |
| `libs/veridoc-fhir/src/veridoc_fhir/extensions.py` | utility | — | `libs/veridoc-audit/src/veridoc_audit/models.py` | partial |
| `libs/veridoc-fhir/tests/conftest.py` | test | — | `libs/veridoc-audit/tests/conftest.py` | exact |
| `libs/veridoc-fhir/tests/test_models.py` | test | — | `libs/veridoc-crypto/tests/test_field_encryption.py` | role-match |
| `libs/veridoc-fhir/tests/test_repository.py` | test | CRUD | `libs/veridoc-audit/tests/conftest.py` | role-match |
| `libs/veridoc-fhir/tests/test_provenance.py` | test | — | `libs/veridoc-audit/tests/test_chain.py` | role-match |
| `libs/veridoc-ingestion/pyproject.toml` | config | — | `libs/veridoc-crypto/pyproject.toml` | exact |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py` | utility | request-response | `libs/veridoc-crypto/src/veridoc_crypto/kms.py` | exact |
| `libs/veridoc-ingestion/src/veridoc_ingestion/registry.py` | utility | request-response | `libs/veridoc-auth/src/veridoc_auth/allowlist.py` | partial |
| `libs/veridoc-ingestion/src/veridoc_ingestion/ocr_engine.py` | utility | file-I/O | `libs/veridoc-crypto/src/veridoc_crypto/kms.py` | exact |
| `libs/veridoc-ingestion/src/veridoc_ingestion/blob_store.py` | utility | file-I/O | `libs/veridoc-crypto/src/veridoc_crypto/kms.py` | exact |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/native_fhir.py` | service | transform | `libs/veridoc-crypto/src/veridoc_crypto/kms.py` (concrete impl pattern) | role-match |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/hl7v2.py` | service | transform | `libs/veridoc-crypto/src/veridoc_crypto/kms.py` (concrete impl pattern) | role-match |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/pdf_excel.py` | service | file-I/O | `libs/veridoc-crypto/src/veridoc_crypto/kms.py` (concrete impl pattern) | role-match |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/ocr.py` | service | file-I/O | `libs/veridoc-crypto/src/veridoc_crypto/kms.py` (concrete impl pattern) | role-match |
| `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/proprietary.py` | service | — | `libs/veridoc-crypto/src/veridoc_crypto/kms.py` (stub pattern) | exact |
| `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py` | utility | transform | `services/reference-service/src/reference_service/api/subjects.py` | partial |
| `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py` | service | event-driven | `libs/veridoc-audit/src/veridoc_audit/sdk.py` | partial |
| `libs/veridoc-ingestion/tests/conftest.py` | test | — | `libs/veridoc-audit/tests/conftest.py` | exact |
| `libs/veridoc-ingestion/tests/test_adapters.py` | test | — | `services/reference-service/tests/test_subject.py` | role-match |
| `libs/veridoc-ingestion/tests/test_ocr_engine.py` | test | — | `libs/veridoc-crypto/tests/test_field_encryption.py` | role-match |
| `libs/veridoc-ingestion/tests/test_blob_store.py` | test | — | `libs/veridoc-crypto/tests/test_field_encryption.py` | role-match |
| `services/ingestion-service/src/ingestion_service/config.py` | config | — | `services/reference-service/src/reference_service/config.py` | exact |
| `services/ingestion-service/src/ingestion_service/main.py` | controller | request-response | `services/reference-service/src/reference_service/main.py` | exact |
| `services/ingestion-service/src/ingestion_service/api/ingest.py` | controller | request-response | `services/reference-service/src/reference_service/api/subjects.py` | role-match |
| `services/ingestion-service/src/ingestion_service/worker_main.py` | service | event-driven | `services/reference-service/src/reference_service/migrate.py` (entrypoint pattern) | partial |
| `services/ingestion-service/Dockerfile` | config | — | `services/reference-service/Dockerfile` | exact |
| `services/ingestion-service/tests/conftest.py` | test | — | `services/reference-service/tests/conftest.py` | exact |
| `deploy/helm/veridoc/templates/mongodb.yaml` | config | — | `deploy/helm/veridoc/templates/postgres.yaml` | exact |
| `deploy/helm/veridoc/templates/minio.yaml` | config | — | `deploy/helm/veridoc/templates/redis.yaml` | exact |
| `deploy/helm/veridoc/templates/ingestion-service.yaml` | config | — | `deploy/helm/veridoc/templates/reference-service.yaml` | exact |
| `deploy/helm/veridoc/values.yaml` (modified) | config | — | `deploy/helm/veridoc/values.yaml` (existing) | exact |

---

## Pattern Assignments

### `libs/veridoc-fhir/pyproject.toml` (config)

**Analog:** `libs/veridoc-crypto/pyproject.toml`

**Full pyproject.toml pattern** (lines 1-14):
```toml
[project]
name = "veridoc-crypto"
version = "0.0.0"
description = "..."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "tink>=1.10",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/veridoc_crypto"]
```

**Apply to `veridoc-fhir`:** Replace package name, description, and dependencies with:
```toml
dependencies = [
    "fhir.resources>=8.2.0",
    "pymongo>=4.17.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/veridoc_fhir"]
```

The root `pyproject.toml` `[tool.uv.sources]` block (lines 21-26) must gain two new entries:
```toml
veridoc-fhir = { workspace = true }
veridoc-ingestion = { workspace = true }
```

---

### `libs/veridoc-fhir/src/veridoc_fhir/models.py` (model, transform)

**Analog:** `libs/veridoc-audit/src/veridoc_audit/models.py`

**Module-level `__all__` + import discipline pattern** (audit models.py, lines 1-33):
```python
"""..."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict
# ... imports

__all__ = ["AuditEvent", "AuditLog", "Base"]
```

**Apply to `veridoc_fhir/models.py`:** Use the same `from __future__ import annotations`,
`__all__` gating, and module docstring pattern. The critical `fhir.resources` import discipline
(from RESEARCH.md):
```python
# CRITICAL: always R4B sub-package — top-level now resolves to R5 (since v7.0.0)
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

__all__ = [
    "Patient", "Encounter", "Observation", "Condition",
    "MedicationRequest", "AdverseEvent", "DiagnosticReport",
    "DocumentReference", "Procedure", "Provenance",
]
```

The `__all__` re-export is the enforcement mechanism that prevents any future code from accidentally
importing the R5 top-level namespace instead of R4B.

---

### `libs/veridoc-fhir/src/veridoc_fhir/repository.py` (service, CRUD)

**Analog:** `services/reference-service/src/reference_service/db.py` (session/engine factory
pattern) + RESEARCH.md Pattern 3 (FhirRepository shape).

**Session factory factory + scope pattern** (`db.py` lines 19-44):
```python
def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    return create_engine(url, future=True, pool_pre_ping=True)

def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)

def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

**Apply to `FhirRepository`:** Mirror the constructor-injects-client, method-per-operation
pattern. The `session_scope` equivalent for MongoDB is `AsyncMongoClient` passed at construction
(no transaction scope needed — MongoDB upsert is not transactional in this design). The
`create_indexes()` method MUST be called at FastAPI `lifespan` startup (see `main.py` pattern
below).

**Concrete startup hook pattern** (from RESEARCH.md Code Examples):
```python
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

### `libs/veridoc-fhir/src/veridoc_fhir/provenance.py` (utility, transform)

**Analog:** `services/reference-service/src/reference_service/api/subjects.py` (provenance
metadata embedded in audit event, lines 120-143).

The pattern from `subjects.py` is: compute metadata (pseudonym token, ciphertext digest),
embed it in a structured dict, and write it atomically with the business operation. For FHIR
provenance, the equivalent is: after `FhirRepository.save()` returns the resource ID, call
`create_provenance()` and save that Provenance resource too.

**Datetime pattern** (`subjects.py` line 121):
```python
from datetime import UTC, datetime
# ...
occurred_at=datetime.now(UTC),
```
Apply identically to `Provenance.recorded` — always timezone-aware (`datetime.now(timezone.utc).isoformat()`).

**`before`/`after` carry already-pseudonymized values** (`subjects.py` lines 133-141):
```python
after={
    "pseudonym_token": token,
    "pii_ciphertext_sha256": _ct_digest(ciphertext),
    "pii_ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
},
```
Apply to provenance: the `entity.what.reference` in the Provenance resource must be the
pseudonymized patient reference, never the natural_id.

---

### `libs/veridoc-fhir/tests/conftest.py` (test, testcontainers)

**Analog:** `libs/veridoc-audit/tests/conftest.py`

**Testcontainers + env-var-first pattern** (lines 48-85):
```python
@pytest.fixture(scope="session")
def db_url():
    env_url = os.environ.get("VERIDOC_TEST_DATABASE_URL")
    if env_url:
        yield _normalize_url(env_url)
        return
    try:
        from testcontainers.postgres import PostgresContainer
    except Exception:
        pytest.skip("no VERIDOC_TEST_DATABASE_URL and testcontainers unavailable")
    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:
        pytest.skip(f"no VERIDOC_TEST_DATABASE_URL and Docker unavailable: {exc}")
    try:
        yield _normalize_url(container.get_connection_url())
    finally:
        container.stop()
```

**Apply to `veridoc-fhir/tests/conftest.py`:** Replace `PostgresContainer` with MongoDB:
```python
from testcontainers.mongodb import MongoDbContainer
# env var: VERIDOC_TEST_MONGODB_URL
container = MongoDbContainer("mongo:7-jammy")
```
Keep the three-path resolution (env var → testcontainers → skip) and the `scope="session"`
for the container but `scope="function"` for the per-test DB state (drop/recreate the
`fhir_resources` collection between tests for isolation).

---

### `libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py` (utility, request-response)

**Analog:** `libs/veridoc-crypto/src/veridoc_crypto/kms.py` — the ABC + concrete-impls +
`# pragma: no cover` stub pattern.

**Full ABC pattern** (`kms.py` lines 65-80):
```python
class KMSKeyring(abc.ABC):
    """Provider-portable KMS interface: wrap/unwrap a DEK with a wrapping key.

    Implementations: LocalKeyring (tests), AwsKmsKeyring, AzureKeyVaultKeyring.
    """

    @abc.abstractmethod
    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        """Encrypt (wrap) a DEK under the wrapping key; returns the wrapped DEK."""

    @abc.abstractmethod
    def unwrap_dek(self, wrapping_key: bytes, wrapped: bytes, aad: bytes = b"") -> bytes:
        """Decrypt (unwrap) a wrapped DEK under the wrapping key; returns the DEK."""
```

**Apply to `SourceAdapter`:** Mirror exactly — ABC with `@abc.abstractmethod` for `ingest()`.
The `SourceProfile` dataclass follows the same file; `SourceModality` is a `StrEnum` (same
module as the ABC). Copy the docstring discipline: describe implementations, not just the method.

---

### `libs/veridoc-ingestion/src/veridoc_ingestion/ocr_engine.py` (utility, file-I/O)

**Analog:** `libs/veridoc-crypto/src/veridoc_crypto/kms.py` — identical ABC + local-impl +
cloud-stubs structure.

**Local impl + cloud stubs pattern** (`kms.py` lines 82-135):
```python
class LocalKeyring(KMSKeyring):
    """In-process keyring for tests/local dev — no cloud account required."""

    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        return aead_from_raw_key(wrapping_key).encrypt(dek, aad)

    def unwrap_dek(self, wrapping_key: bytes, wrapped: bytes, aad: bytes = b"") -> bytes:
        return aead_from_raw_key(wrapping_key).decrypt(wrapped, aad)


class AwsKmsKeyring(KMSKeyring):  # pragma: no cover - interface stub (no live calls)
    """AWS KMS adapter (interface only this phase; DEC-cloud-provider OPEN)."""

    def __init__(self, key_arn: str) -> None:
        self.key_arn = key_arn

    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        raise NotImplementedError(
            "AwsKmsKeyring is a portability stub this phase; wire Tink AWS KMS "
            "when DEC-cloud-provider closes to AWS"
        )
```

**Apply to `OcrEngine`:** `TesseractEngine` = `LocalKeyring` (real working impl, no
`# pragma: no cover`). `TextractEngine` and `AzureDocumentIntelligenceEngine` = cloud stubs
with `# pragma: no cover - DEC-cloud-provider OPEN` and identical `NotImplementedError` with
the wire-when message.

**`OcrResult` dataclass** lives in the same file (no separate models file for this lib):
```python
@dataclass
class OcrResult:
    text: str
    document_confidence: float    # 0.0–1.0; mean of per-word conf > 0
    word_confidences: list[float]
    flagged: bool                 # True if document_confidence < 0.95
    escalated: bool               # True if document_confidence < 0.85
```

---

### `libs/veridoc-ingestion/src/veridoc_ingestion/blob_store.py` (utility, file-I/O)

**Analog:** `libs/veridoc-crypto/src/veridoc_crypto/kms.py` — same ABC + local-impl + cloud-stubs.

The `S3BlobStore` maps to `LocalKeyring` (real working impl); a future `AzureBlobStore` maps
to `AzureKeyVaultKeyring` (stub). The `endpoint_url` conditional enables MinIO locally and
real S3 in production without code changes — mirror how `LocalKeyring` vs `AwsKmsKeyring`
differ only in where the key operation executes.

**Pragma + NotImplementedError stub pattern** (`kms.py` lines 95-115):
```python
class AwsKmsKeyring(KMSKeyring):  # pragma: no cover - interface stub (no live calls)
    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        raise NotImplementedError(
            "AwsKmsKeyring is a portability stub this phase; wire Tink AWS KMS "
            "when DEC-cloud-provider closes to AWS"
        )
```

**Apply for `AzureBlobStore`:**
```python
class AzureBlobStore(BlobStore):  # pragma: no cover - DEC-cloud-provider OPEN
    def put(self, key: str, data: bytes, content_type: str) -> str:
        raise NotImplementedError(
            "AzureBlobStore is a portability stub; wire azure-storage-blob "
            "when DEC-cloud-provider closes to Azure"
        )
```

---

### `libs/veridoc-ingestion/src/veridoc_ingestion/adapters/proprietary.py` (service, stub)

**Analog:** `libs/veridoc-crypto/src/veridoc_crypto/kms.py` (`AwsKmsKeyring` / `AzureKeyVaultKeyring`
stub pattern, lines 95-135).

The proprietary adapter IS the stub pattern — it conforms to `SourceAdapter` interface, raises
`NotImplementedError` with a message explaining when it will be wired. Copy the `# pragma: no cover`
class comment and the exact `NotImplementedError` message discipline:
```python
class ProprietaryAdapter(SourceAdapter):  # pragma: no cover - no real contract to test (D-11)
    """Proprietary-API adapter (interface only this milestone; D-11).

    When a real proprietary contract is available, this implementation wires the vendor API.
    """

    def ingest(self, payload: bytes, profile: SourceProfile) -> list:
        raise NotImplementedError(
            "ProprietaryAdapter is an interface stub this phase; wire the vendor API "
            "when a proprietary contract is available for testing"
        )
```

---

### `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py` (service, event-driven)

**Analog:** `libs/veridoc-audit/src/veridoc_audit/sdk.py` (session ownership + advisory lock
pattern) for the audit write boundary; `services/reference-service/src/reference_service/db.py`
for `session_scope`.

**Critical deviation from Phase 1 pattern** — the `session_scope` pattern from `db.py` (lines
31-44) applies, but the worker owns the commit (not the HTTP handler):
```python
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Workers MUST open their own `Session` and commit explicitly (D-06 deviation):
```python
# In RQ worker function — NOT in the FastAPI handler
with session_scope(session_factory) as session:
    append_audit(session, AuditEvent(...))
    session.commit()   # worker owns the commit
```

**`append_audit` import pattern** (`subjects.py` line 27):
```python
from veridoc_audit import AuditEvent, append_audit
```

**RQ job function signature** (JSON-serializable primitives only — no raw bytes):
```python
def ingest_job(
    site_id: str,
    modality: str,
    payload_key: str,   # blob store key (string) — NOT raw bytes
    tenant_id: str,
    actor_id: str,
) -> dict:
    """RQ job. Opens its own DB session; calls append_audit; commits."""
```

---

### `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py` (utility, transform)

**Analog:** `services/reference-service/src/reference_service/api/subjects.py` (pseudonym +
audit payload construction, lines 109-143) for the pseudonymization integration pattern.

**Pseudonym call pattern** (`subjects.py` lines 109-110):
```python
from veridoc_pseudonym import pseudonym_token
# ...
token = pseudonym_token(body.natural_id, body.natural_id)
```

**Apply to HL7 mapping:** `pseudonym_token(patient_id, pid_3_value)` where `pid_3_value` is
the raw ID component (PID.3.1, stripped of assigning authority). The `patient_id` is the
cross-source stable key (same patient_id must be used for the same real patient across all
adapters — documented in this file as per RESEARCH.md open question #3).

---

### `services/ingestion-service/src/ingestion_service/config.py` (config)

**Analog:** `services/reference-service/src/reference_service/config.py` — exact clone with
new fields.

**Full Settings pattern** (`config.py` lines 1-57):
```python
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERIDOC_", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://localhost/veridoc",
        description="SQLAlchemy URL for the service Postgres (psycopg v3 driver).",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    keycloak_issuer: str = Field(default="https://kc.veridoc.local/realms/veridoc")
    keycloak_jwks_uri: str = Field(...)
    keycloak_audience: str = Field(default="reference-service")
    keycloak_client_id: str = Field(default="reference-service")
    kms_master_key_uri: str = Field(default="local://dev-master-key")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**New fields to add** (same pattern, same `env_prefix="VERIDOC_"`, same `Field` discipline):
```python
mongodb_url: str = Field(
    default="mongodb://localhost:27017/veridoc_fhir",
    description="AsyncMongoClient URL for the FHIR document store (D-02).",
)
blob_endpoint_url: str | None = Field(
    default=None,
    description="S3-compatible endpoint URL; None = real AWS S3; set to MinIO URL locally.",
)
blob_bucket: str = Field(default="veridoc-docs")
blob_access_key: str = Field(default="")
blob_secret_key: str = Field(default="")
```

---

### `services/ingestion-service/src/ingestion_service/main.py` (controller, request-response)

**Analog:** `services/reference-service/src/reference_service/main.py` — near-exact clone.

**Full app factory pattern** (`main.py` lines 86-139):
```python
def create_app(
    *,
    engine: Engine | None = None,
    jwks: JWKSCache | None = None,
    issuer: str | None = None,
    audience: str | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    # ...
    app = FastAPI(title="VeriDoc Reference Service", version="0.1.0")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.jwks = jwks

    @app.exception_handler(AuthError)
    async def _auth_error(_request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(TenancyError)
    async def _tenancy_error(_request: Request, exc: TenancyError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    principal_dependency = _make_principal_dependency(jwks=jwks, issuer=issuer, audience=audience)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(ingest.router, dependencies=[Depends(principal_dependency)])
    return app

app = create_app()
```

**Additions for ingestion-service:** The `create_app` function gains a `lifespan` parameter
for the MongoDB + RQ queue startup (pattern from RESEARCH.md):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # MongoDB indexes created once at startup (Pitfall 6 guard)
    repo = FhirRepository(mongo_url=settings.mongodb_url)
    await repo.create_indexes()
    app.state.fhir_repo = repo
    # RQ queue with JSONSerializer (Pitfall 3 guard)
    from redis import Redis
    from rq import Queue
    from rq.serializers import JSONSerializer
    app.state.rq_queue = Queue(
        "ingestion",
        connection=Redis.from_url(settings.redis_url),
        serializer=JSONSerializer,
    )
    yield
    repo._client.close()

app = FastAPI(title="VeriDoc Ingestion Service", lifespan=lifespan)
```

The `_bearer_token` helper and `_make_principal_dependency` factory are copied verbatim from
`reference-service/main.py` lines 32-83 — no changes needed.

---

### `services/ingestion-service/src/ingestion_service/api/ingest.py` (controller, request-response)

**Analog:** `services/reference-service/src/reference_service/api/subjects.py` — the
five-lib composition pattern.

**RBAC deny-by-default pattern** (`subjects.py` lines 40-52):
```python
_WRITE_ROLES = ("site-coordinator", "data-manager", "principal-investigator")

router = APIRouter(prefix="/subjects", tags=["subjects"])

def require_write_role(request: Request) -> Principal:
    principal: Principal | None = getattr(request.state, "principal", None)
    if principal is None:
        from veridoc_auth import AuthError
        raise AuthError("no authenticated principal on request")
    check_roles(principal, _WRITE_ROLES)
    return principal
```

**Apply to `/ingest/{site_id}`:** Copy deny-by-default pattern; roles for ingest are
`"site-coordinator"` and `"data-manager"`. The handler body enqueues an RQ job (not a direct
DB write) and returns a `202 Accepted` with job ID.

**Request-session dependency pattern** (`subjects.py` lines 86-93):
```python
def get_session(request: Request) -> Session:
    factory = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()
```

Copy verbatim — the ingest endpoint still needs a Postgres session for the immediate
"job enqueued" audit write (separate from the worker's job-completion audit).

**Tenancy pattern** (`subjects.py` lines 103-104):
```python
tenant = current_tenant()  # fail-closed: raises TenancyError -> 401 if unresolved
tenant_id = f"{tenant.site}/{tenant.study}"
```

Copy verbatim — every ingest is tenancy-scoped.

---

### `services/ingestion-service/src/ingestion_service/worker_main.py` (service, event-driven)

**Analog:** `services/reference-service/src/reference_service/migrate.py` (module-level
entrypoint/path-setup pattern, lines 1-10).

This file is the RQ worker process entrypoint. It is not imported by FastAPI — it runs as a
separate process (`rq worker`). Its only job is to start the worker with the correct queue
name, serializer, and connection. The module-docstring-first, `from __future__ import
annotations` pattern from the codebase applies:

```python
"""RQ worker entrypoint for the ingestion-service.

Run as: rq worker ingestion --serializer rq.serializers.JSONSerializer --url $VERIDOC_REDIS_URL
Or via: python -m ingestion_service.worker_main
"""
from __future__ import annotations

from rq import Worker
from rq.serializers import JSONSerializer
from redis import Redis

from .config import get_settings

def main() -> None:
    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    worker = Worker(["ingestion"], connection=conn, serializer=JSONSerializer)
    worker.work()

if __name__ == "__main__":
    main()
```

---

### `services/ingestion-service/Dockerfile` (config)

**Analog:** `services/reference-service/Dockerfile` — near-exact clone.

**Full multi-stage pattern** (`Dockerfile` lines 1-65):
```dockerfile
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY libs/ ./libs/
COPY services/ingestion-service/pyproject.toml ./services/ingestion-service/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package ingestion-service --no-install-project
COPY services/ingestion-service/ ./services/ingestion-service/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package ingestion-service

FROM python:3.12-slim AS runtime
RUN groupadd --system --gid 1001 veridoc \
    && useradd --system --uid 1001 --gid 1001 ...
```

**Additions for ingestion-service Dockerfile:** Add Tesseract system package install in
the builder stage (Pitfall 8 — `TesseractNotFoundError` at runtime if missing):
```dockerfile
# In builder stage, after WORKDIR:
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
```

Also copy the Tesseract binary to the runtime stage (or install it there too):
```dockerfile
# In runtime stage:
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
```

The `CMD` changes to support both the API server and the worker (two separate container
invocations in Kubernetes, same image):
```dockerfile
# Default CMD is the API server; worker override via Deployment command:
CMD ["uvicorn", "ingestion_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `services/ingestion-service/tests/conftest.py` (test)

**Analog:** `services/reference-service/tests/conftest.py` — exact clone with MongoDB
testcontainer added.

**Full conftest pattern** (`conftest.py` lines 1-193): Copy verbatim, then add:
1. MongoDB testcontainer fixture alongside the Postgres one:
```python
@pytest.fixture(scope="session")
def mongo_url():
    env_url = os.environ.get("VERIDOC_TEST_MONGODB_URL")
    if env_url:
        yield env_url
        return
    try:
        from testcontainers.mongodb import MongoDbContainer
    except Exception:
        pytest.skip("no VERIDOC_TEST_MONGODB_URL and testcontainers unavailable")
    try:
        container = MongoDbContainer("mongo:7-jammy")
        container.start()
    except Exception as exc:
        pytest.skip(f"no VERIDOC_TEST_MONGODB_URL and Docker unavailable: {exc}")
    try:
        yield container.get_connection_url()
    finally:
        container.stop()
```

2. MinIO testcontainer fixture:
```python
@pytest.fixture(scope="session")
def minio_endpoint():
    env_url = os.environ.get("VERIDOC_TEST_MINIO_URL")
    if env_url:
        yield env_url
        return
    try:
        from testcontainers.minio import MinioContainer
    except Exception:
        pytest.skip("no VERIDOC_TEST_MINIO_URL and testcontainers unavailable")
    # ...
```

The `mint_token` helper (`conftest.py` lines 148-164), `_fresh_keystore` autouse fixture
(`lines 117-124`), and `create_app` injection pattern (`lines 180-184`) copy verbatim.

---

### `deploy/helm/veridoc/templates/mongodb.yaml` (config, StatefulSet)

**Analog:** `deploy/helm/veridoc/templates/postgres.yaml`

**Full StatefulSet + Service pattern** (`postgres.yaml` lines 1-87):
The MongoDB template copies the Postgres template structure exactly:
- `{{- if .Values.mongodb.enabled }}` guard
- `$component := "mongodb"`, `$name` via `veridoc.componentName`
- `kind: Deployment` (single-node; no StatefulSet needed at kind/CI scale)
- Secret credentials via `secretKeyRef` (never inlined — T-06-01)
- `emptyDir` vs PVC volume controlled by `persistence.enabled`
- Readiness probe and liveness probe

**Secret pattern** (`postgres.yaml` lines 36-43):
```yaml
env:
  - name: MONGO_INITDB_ROOT_USERNAME
    valueFrom:
      secretKeyRef:
        name: {{ .Values.secrets.mongodb.name }}
        key: {{ .Values.secrets.mongodb.usernameKey }}
  - name: MONGO_INITDB_ROOT_PASSWORD
    valueFrom:
      secretKeyRef:
        name: {{ .Values.secrets.mongodb.name }}
        key: {{ .Values.secrets.mongodb.passwordKey }}
```

**Readiness probe** — MongoDB equivalent of `pg_isready`:
```yaml
readinessProbe:
  exec:
    command: ["mongosh", "--eval", "db.adminCommand('ping')"]
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

### `deploy/helm/veridoc/templates/minio.yaml` (config, Deployment)

**Analog:** `deploy/helm/veridoc/templates/redis.yaml`

**Redis Deployment pattern** (`redis.yaml` lines 1-65):
```yaml
{{- if .Values.redis.enabled }}
{{- $component := "redis" }}
{{- $name := include "veridoc.componentName" (dict "component" $component) }}
# ...
command: ["sh", "-c", "exec redis-server --requirepass \"$REDIS_PASSWORD\""]
env:
  - name: REDIS_PASSWORD
    valueFrom:
      secretKeyRef:
        name: {{ .Values.secrets.redis.name }}
        key: {{ .Values.secrets.redis.passwordKey }}
```

**Apply to MinIO:** MinIO uses `MINIO_ROOT_USER` + `MINIO_ROOT_PASSWORD` env vars from a
`veridoc-minio` Secret (same secretKeyRef pattern). The MinIO command:
```yaml
command: ["minio", "server", "/data", "--console-address", ":9001"]
```

Two ports exposed (API 9000, console 9001) vs Redis's single port — add a second containerPort
and Service port entry.

---

### `deploy/helm/veridoc/templates/ingestion-service.yaml` (config, Deployment)

**Analog:** `deploy/helm/veridoc/templates/reference-service.yaml` — exact clone pattern.

**Full Deployment + Service pattern** (`reference-service.yaml` lines 1-107):
Copy verbatim; replace `referenceService` with `ingestionService` in all value path references.

**Additional env vars** not in reference-service (same `secretKeyRef` pattern, T-06-01 compliant):
```yaml
- name: VERIDOC_MONGODB_URL
  value: "mongodb://$(MONGO_USER):$(MONGO_PASSWORD)@veridoc-mongodb:27017/veridoc_fhir"
- name: VERIDOC_BLOB_ENDPOINT_URL
  value: {{ .Values.ingestionService.config.blobEndpointUrl | quote }}
- name: VERIDOC_BLOB_BUCKET
  value: {{ .Values.ingestionService.config.blobBucket | quote }}
- name: VERIDOC_BLOB_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.secrets.minio.name }}
      key: {{ .Values.secrets.minio.usernameKey }}
- name: VERIDOC_BLOB_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.secrets.minio.name }}
      key: {{ .Values.secrets.minio.passwordKey }}
```

The `healthPath: /healthz` pattern and the readiness/liveness probe copy verbatim.

The ingestion-service also runs an **RQ worker Deployment** (separate Deployment, same image,
different `command`). Create a second Deployment block in the same file (or a separate
`ingestion-worker.yaml`):
```yaml
command: ["rq", "worker", "ingestion",
          "--serializer", "rq.serializers.JSONSerializer",
          "--url", "$(VERIDOC_REDIS_URL)"]
```

---

### `deploy/helm/veridoc/values.yaml` (config, modified)

**Analog:** `deploy/helm/veridoc/values.yaml` (existing structure, lines 1-146)

**New sections to append**, following the exact existing block format (YAML section header +
enabled toggle + image block + replicas/port + persistence + resources + config):

```yaml
# ---------------------------------------------------------------------------- #
# MongoDB (D-02) — canonical FHIR R4B document store.
# ---------------------------------------------------------------------------- #
mongodb:
  enabled: true
  image:
    repository: mongo
    tag: "7-jammy"
  replicas: 1
  port: 27017
  database: veridoc_fhir
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  persistence:
    enabled: false   # emptyDir in kind/CI; PVC in prod
    size: 5Gi

# ---------------------------------------------------------------------------- #
# MinIO (D-10) — S3-compatible blob store for retained originals.
# ---------------------------------------------------------------------------- #
minio:
  enabled: true
  image:
    repository: minio/minio
    tag: "RELEASE.2024-01-01T00-00-00Z"  # pin a digest in prod
  replicas: 1
  port: 9000
  consolePort: 9001
  defaultBucket: veridoc-docs
  resources:
    requests:
      cpu: 50m
      memory: 128Mi
    limits:
      cpu: 250m
      memory: 256Mi
  persistence:
    enabled: false

# ---------------------------------------------------------------------------- #
# Ingestion service (D-04).
# ---------------------------------------------------------------------------- #
ingestionService:
  enabled: true
  image:
    repository: veridoc/ingestion-service
    tag: "ci"
  replicas: 1
  port: 8000
  healthPath: /healthz
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "2"
      memory: 1Gi
  config:
    keycloakIssuer: "http://veridoc-keycloak:8080/realms/veridoc"
    keycloakJwksUri: "http://veridoc-keycloak:8080/realms/veridoc/protocol/openid-connect/certs"
    keycloakAudience: "ingestion-service"
    redisUrl: "redis://veridoc-redis:6379/0"
    blobEndpointUrl: "http://veridoc-minio:9000"
    blobBucket: "veridoc-docs"
```

**`secrets:` block additions** (same `name` / `Key` pattern as existing secrets, lines 27-47):
```yaml
  mongodb:
    name: veridoc-mongodb
    usernameKey: MONGO_INITDB_ROOT_USERNAME
    passwordKey: MONGO_INITDB_ROOT_PASSWORD
  minio:
    name: veridoc-minio
    usernameKey: MINIO_ROOT_USER
    passwordKey: MINIO_ROOT_PASSWORD
```

---

## Shared Patterns

### ABC + Local-impl + Cloud-stubs (portability pattern)

**Source:** `libs/veridoc-crypto/src/veridoc_crypto/kms.py` (lines 65-135)
**Apply to:** `ocr_engine.py`, `blob_store.py`, `adapter.py`

Three-part structure that EVERY new abstraction must follow:
1. `class XyzABC(abc.ABC)` — the interface, `@abc.abstractmethod` on every operation
2. `class LocalXyz(XyzABC)` — working implementation (Tesseract / S3+MinIO / adapter-with-real-logic)
3. `class CloudXyz(XyzABC): # pragma: no cover - DEC-cloud-provider OPEN` — stub with
   `raise NotImplementedError("... wire when DEC-cloud-provider closes to ...")`

Key excerpt (`kms.py` lines 95-115):
```python
class AwsKmsKeyring(KMSKeyring):  # pragma: no cover - interface stub (no live calls)
    """AWS KMS adapter (interface only this phase; DEC-cloud-provider OPEN).

    When DEC-cloud-provider closes to AWS, this wires Tink's AWS KMS integration so
    the DEK is wrapped by a KMS-resident key reference instead of a local key.
    """

    def __init__(self, key_arn: str) -> None:
        self.key_arn = key_arn

    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        raise NotImplementedError(
            "AwsKmsKeyring is a portability stub this phase; wire Tink AWS KMS "
            "when DEC-cloud-provider closes to AWS"
        )
```

### Authentication + Tenancy + RBAC (request guard)

**Source:** `services/reference-service/src/reference_service/main.py` (lines 32-83) +
`services/reference-service/src/reference_service/api/subjects.py` (lines 40-52)
**Apply to:** `services/ingestion-service/src/ingestion_service/main.py` and `api/ingest.py`

The `_make_principal_dependency` factory and `require_write_role` pattern copy verbatim.
Every protected route uses `Depends(principal_dependency)` at the router level plus
`Depends(require_write_role)` at the handler level.

### Audit Write (same-transaction vs worker-commit)

**Source:** `libs/veridoc-audit/src/veridoc_audit/sdk.py` (lines 30-70) + `services/reference-service/src/reference_service/api/subjects.py` (lines 121-144)
**Apply to:** `services/ingestion-service/src/ingestion_service/api/ingest.py` (job-enqueue audit) + `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py` (job-completion audit)

Two distinct audit patterns in this phase:

**Pattern A — same-transaction (enqueue event in HTTP handler):**
```python
# In the HTTP handler — same pattern as subjects.py lines 121-144
append_audit(session, AuditEvent(action="ingest:enqueued", ...))
session.commit()  # business row + audit row atomic
```

**Pattern B — worker-owned session (job-completion in RQ worker, D-06 deviation):**
```python
# In the RQ worker function — worker opens and commits its own session
with session_scope(session_factory) as session:
    append_audit(session, AuditEvent(action="ingest:completed", ...))
    session.commit()  # worker owns the commit (D-06 deviation from Phase 1 default)
```

`append_audit` signature is identical in both cases; only the session lifecycle differs.

### Pseudonymization at Ingestion

**Source:** `libs/veridoc-pseudonym/src/veridoc_pseudonym/pseudonym.py` (lines 28-35) +
`services/reference-service/src/reference_service/api/subjects.py` (lines 109-110)
**Apply to:** All `SourceAdapter` implementations (`native_fhir.py`, `hl7v2.py`, `pdf_excel.py`, `ocr.py`)

```python
from veridoc_pseudonym import pseudonym_token
# ...
token = pseudonym_token(patient_id, natural_id)
# patient_id: stable cross-source key (e.g. site_id + internal MRN)
# natural_id: the source-specific identifier (PID.3.1 for HL7, patient.id for FHIR)
```

Every adapter MUST call `pseudonym_token` and replace all PII fields with the token BEFORE
calling `FhirRepository.save()`. The `patient_id` argument must be consistent across sources
(same real patient = same `patient_id` input = same token output). This is the SDV matching
precondition for Phase 5.

### Testcontainers + env-var-first Resolution

**Source:** `libs/veridoc-audit/tests/conftest.py` (lines 48-85) + `services/reference-service/tests/conftest.py` (lines 67-85)
**Apply to:** `libs/veridoc-fhir/tests/conftest.py`, `libs/veridoc-ingestion/tests/conftest.py`, `services/ingestion-service/tests/conftest.py`

Three-path resolution (env var → testcontainers → `pytest.skip()`) with `scope="session"` for
the container. The `_normalize_url` driver-prefix normalizer from `conftest.py` lines 49-58
copies verbatim for Postgres; new conftest files add MongoDB and MinIO equivalents.

### Error Handling (HTTP boundary)

**Source:** `services/reference-service/src/reference_service/main.py` (lines 107-119)
**Apply to:** `services/ingestion-service/src/ingestion_service/main.py`

```python
@app.exception_handler(AuthError)
async def _auth_error(_request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})

@app.exception_handler(ForbiddenError)
async def _forbidden(_request: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})

@app.exception_handler(TenancyError)
async def _tenancy_error(_request: Request, exc: TenancyError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})
```

Copy verbatim. No PII in error messages — `str(exc)` is the lib's controlled message.

### pyproject.toml + Hatchling Build Layout

**Source:** `libs/veridoc-crypto/pyproject.toml` (lines 1-14) — minimal lib pattern.
**Apply to:** `libs/veridoc-fhir/pyproject.toml`, `libs/veridoc-ingestion/pyproject.toml`

All libs use hatchling, `src/<pkg>` layout, `packages = ["src/veridoc_<name>"]`, no
`[tool.hatch.build.targets.wheel]` deviations. The root `pyproject.toml` `[tool.uv.sources]`
and `[tool.uv.workspace]` are auto-satisfied by the `members = ["libs/*", "services/*"]`
glob — no manual addition to the `members` list is needed, but `veridoc-fhir` and
`veridoc-ingestion` MUST be added to `[tool.uv.sources]` with `{ workspace = true }`.

### CI Workflow Delta

**Source:** `.github/workflows/ci.yml` (the `deploy-kind` job, lines 100-168)
**Apply to:** `.github/workflows/ci.yml` (modified — no new file)

The `deploy-kind` job's diagnose step (lines 135-148) lists specific deployment names.
Add `veridoc-mongodb`, `veridoc-minio`, `veridoc-ingestion-service` to the loop:
```bash
for d in veridoc-postgres veridoc-redis veridoc-keycloak veridoc-reference-service \
          veridoc-mongodb veridoc-minio veridoc-ingestion-service; do
```

The smoke test step (lines 149-166) adds an ingestion smoke test:
```bash
# After the existing tamper-detection test:
uv run pytest services/ingestion-service/tests/test_ingest_api.py -q
```

---

## No Analog Found

All files have analogs. The following files have no **exact** analog but have **role-match**
analogs sufficient for pattern extraction:

| File | Role | Data Flow | Note |
|---|---|---|---|
| `libs/veridoc-fhir/src/veridoc_fhir/repository.py` | service | CRUD | No async MongoDB client in codebase; the Postgres `session_scope` pattern covers session lifecycle; the actual `AsyncMongoClient` API is from RESEARCH.md Pattern 3 |
| `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py` | service | event-driven | No RQ workers in codebase yet; the audit session-scope pattern from `db.py`/`sdk.py` covers the DB boundary; the RQ `Queue`/`Worker` API is from RESEARCH.md Pattern 7 |
| `libs/veridoc-ingestion/src/veridoc_ingestion/mapping/hl7v2_fhir.py` | utility | transform | No HL7 parsing in codebase; `hl7apy` API is from RESEARCH.md Pattern 8; pseudonymization integration is from `subjects.py` |

---

## Metadata

**Analog search scope:** `libs/`, `services/`, `deploy/`, `.github/`
**Files scanned:** 42 source files read; 15 files read in full
**Pattern extraction date:** 2026-06-11
