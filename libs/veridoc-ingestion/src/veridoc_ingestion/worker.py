"""RQ worker job function for the ingestion pipeline (D-06).

Provides :func:`ingest_job` — the RQ job function that runs in a forked worker
process — and :func:`make_queue` — the factory that creates the RQ queue with the
mandatory JSONSerializer.

Design decisions
----------------
- **JSONSerializer only (T-02-SVC-03 / Pitfall 3):** :func:`make_queue` always passes
  ``serializer=JSONSerializer``.  Default pickle is an RCE vector — never use it.
- **JSON-serializable args only (Pitfall 4 anti-pattern "raw bytes in RQ jobs"):**
  :func:`ingest_job` receives a ``payload_key`` string (blob store key), NOT raw bytes.
  The worker fetches the bytes from the blob store at runtime.
- **Worker owns the DB session and commit (D-06 deviation from Phase 1):** RQ workers
  run in forked processes with no shared FastAPI session.  The worker opens its own
  ``session_scope`` session, calls ``append_audit``, and commits.  This is the
  deliberate deviation from the Phase 1 same-transaction pattern (Pitfall 4).
- **asyncio.run inside a sync worker function:** FhirRepository is async; the RQ
  worker is sync.  We run all async Mongo calls via ``asyncio.run``.

Threat mitigations
------------------
- T-02-SVC-03: JSONSerializer eliminates pickle RCE.
- T-02-SVC-04: "ingest:completed" audit event committed by the worker (D-06).

Pattern analogs
---------------
- Session ownership: ``services/reference-service/src/reference_service/db.py``
  :func:`session_scope` (lines 30-44).
- Audit write: ``libs/veridoc-audit/src/veridoc_audit/sdk.py``
  :func:`append_audit` (never commits — worker owns the commit here).
- RESEARCH.md Pattern 7: the canonical RQ job function signature + queue factory.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from rq import Queue
from rq.serializers import JSONSerializer
from redis import Redis

__all__ = ["ingest_job", "make_queue"]


def make_queue(redis_url: str) -> Queue:
    """Return a ``Queue("ingestion", …)`` with :data:`JSONSerializer`.

    JSONSerializer is REQUIRED — default pickle is an RCE vector (Pitfall 3,
    T-02-SVC-03). Calls with ``serializer=JSONSerializer`` are the enforcement
    mechanism; the ``rq worker`` CLI counterpart uses ``--serializer
    rq.serializers.JSONSerializer``.

    Args:
        redis_url: Redis connection URL (e.g. ``"redis://localhost:6379/0"``).

    Returns:
        An ``rq.Queue`` on the ``"ingestion"`` channel using JSONSerializer.
    """
    conn = Redis.from_url(redis_url)
    return Queue("ingestion", connection=conn, serializer=JSONSerializer)


@contextmanager
def _session_scope(db_url: str) -> Iterator:
    """Open a fresh SQLAlchemy session and yield it; rollback on error, always close.

    Mirrors ``services/reference-service/src/reference_service/db.py:session_scope``.
    The worker owns the commit — append_audit never commits (D-05/D-06).

    Args:
        db_url: SQLAlchemy database URL (psycopg v3 driver).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, future=True, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


async def _async_ingest(
    *,
    site_id: str,
    modality: str,
    payload_key: str,
    tenant_id: str,
    actor_id: str,
    blob_endpoint_url: str | None,
    blob_bucket: str,
    blob_access_key: str,
    blob_secret_key: str,
    mongo_url: str,
) -> dict:
    """Async core of the ingest job: blob → adapter → Mongo.

    Separated so ``ingest_job`` can call it via ``asyncio.run`` from the sync RQ
    worker context without blocking the event loop.

    Returns:
        dict with ``resource_ids`` (list), ``provenance_id`` (str),
        and optionally ``ocr_confidence`` (float).
    """
    from veridoc_ingestion.blob_store import S3BlobStore
    from veridoc_ingestion.adapter import SourceProfile, SourceModality
    from veridoc_ingestion.registry import SourceProfileRegistry
    from veridoc_fhir.repository import FhirRepository
    from veridoc_fhir.provenance import create_provenance

    # 1. Fetch the original bytes from the blob store (payload_key is a string — Pitfall 4)
    blob_store = S3BlobStore(
        bucket=blob_bucket,
        endpoint_url=blob_endpoint_url,
        access_key=blob_access_key,
        secret_key=blob_secret_key,
    )
    payload_bytes = blob_store.get(payload_key)

    # 2. Resolve the adapter via the registry
    #    Build a transient registry with the job's site profile (the service-level registry
    #    is not shared with forked workers — workers reconstruct what they need).
    #    WR-03: fail CLOSED on an unrecognized modality. Do NOT fall back to native
    #    FHIR — that would run the wrong parser on PHI bytes and mask routing bugs.
    #    An invalid modality string raises ValueError, which RQ records as a failed
    #    job (dead-letter) rather than silently mis-ingesting.
    mod = SourceModality(modality)

    profile = SourceProfile(site_id=site_id, modality=mod, config={})
    registry = SourceProfileRegistry()
    registry.register(profile)
    adapter = registry.get_adapter(site_id)

    # 3. Run the adapter (sync; adapters are not async)
    resources = adapter.ingest(payload_bytes, profile)

    # 4. Persist resources to MongoDB.
    #    WR-02: wrap repo usage in try/finally so the AsyncMongoClient is always
    #    closed — an exception mid-batch must not leak the client/connection.
    repo = FhirRepository(mongo_url=mongo_url)
    try:
        await repo.create_indexes()

        resource_ids: list[str] = []
        patient_id: str | None = None

        for resource in resources:
            rid = await repo.save(resource)
            resource_ids.append(rid)
            # Track patient_id for Provenance target ref.
            # CR-03: fhir.resources models expose the classmethod get_resource_type();
            # there is no `resource_type` attribute (AttributeError otherwise).
            if resource.get_resource_type() == "Patient" and patient_id is None:
                patient_id = resource.id or rid

        # 5. Create and persist a Provenance resource for this ingest batch
        target_ref = f"Patient/{patient_id}" if patient_id else f"Batch/{site_id}"
        source_urn = f"urn:veridoc:source:{modality}:{site_id}"
        provenance = create_provenance(
            target_ref=target_ref,
            source=source_urn,
            ingestion_path=modality,
            actor_ref="Device/ingestion-service",
        )
        provenance_id = await repo.save(provenance)
        resource_ids.append(provenance_id)

        # 6. Retain the original to blob (already in blob store — retain is a no-op
        #    here; the payload_key IS the retention key pointing to the original).
        #    The original was stored by the API handler before enqueuing; the worker
        #    only fetches and processes it (fulfils "retain the original").

        return {
            "resource_ids": resource_ids,
            "provenance_id": provenance_id,
            "patient_id": patient_id,
        }
    finally:
        repo.close()


def ingest_job(
    site_id: str,
    modality: str,
    payload_key: str,
    tenant_id: str,
    actor_id: str,
    *,
    blob_endpoint_url: str | None = None,
    blob_bucket: str = "",
    blob_access_key: str = "",
    blob_secret_key: str = "",
    mongo_url: str = "",
    db_url: str = "",
) -> dict:
    """RQ job function: fetch payload → adapter → Mongo + Provenance → audit commit.

    Runs in a forked RQ worker process. All arguments MUST be JSON-serializable
    primitives (strings, not bytes — Pitfall 4 / T-02-SVC-03).

    The function:
    1. Fetches the payload bytes from the blob store by ``payload_key`` (a string key,
       never raw bytes — Pitfall 4).
    2. Resolves the adapter from the registry for ``site_id`` / ``modality``.
    3. Runs ``adapter.ingest(payload_bytes, profile)`` → list of FHIR R4B resources.
    4. Saves each resource + a Provenance to MongoDB via :class:`FhirRepository`.
    5. Opens its own SQLAlchemy session, calls :func:`append_audit` with action
       ``"ingest:completed"``, and commits (D-06 deviation: worker owns the commit).
    6. Returns a JSON-serializable result dict.

    Connection parameters (``blob_*``, ``mongo_url``, ``db_url``) are passed as
    explicit keyword arguments so the function can be called directly in tests
    without requiring environment variables. When called by the RQ worker process
    they can also be read from env as a fallback.

    Args:
        site_id: Clinical-site identifier.
        modality: Ingestion modality string (e.g. ``"native-fhir"``).
        payload_key: Blob store object key (string — NOT raw bytes; Pitfall 4).
        tenant_id: Tenancy scope for the audit event (e.g. ``"site/study"``).
        actor_id: The authenticated user/service that initiated the ingest.
        blob_endpoint_url: S3-compatible endpoint URL (MinIO local/CI; None=real S3).
        blob_bucket: Blob bucket name.
        blob_access_key: Blob store access key.
        blob_secret_key: Blob store secret key.
        mongo_url: MongoDB connection URL for :class:`FhirRepository`.
        db_url: PostgreSQL connection URL for the audit write (D-06).

    Returns:
        JSON-serializable dict::

            {
                "resource_ids": ["<id1>", "<id2>", ...],
                "provenance_id": "<prov_id>",
                "patient_id": "<pseudo_patient_id>",
            }
    """
    # Resolve connection params from env as fallback (when called by the RQ worker process)
    _blob_endpoint = blob_endpoint_url or os.environ.get("VERIDOC_BLOB_ENDPOINT_URL")
    _blob_bucket = blob_bucket or os.environ.get("VERIDOC_BLOB_BUCKET", "veridoc-docs")
    _blob_access_key = blob_access_key or os.environ.get("VERIDOC_BLOB_ACCESS_KEY", "")
    _blob_secret_key = blob_secret_key or os.environ.get("VERIDOC_BLOB_SECRET_KEY", "")
    _mongo_url = mongo_url or os.environ.get("VERIDOC_MONGODB_URL", "mongodb://localhost:27017")
    _db_url = db_url or os.environ.get("VERIDOC_DATABASE_URL", "postgresql+psycopg://localhost/veridoc")

    # Run async Mongo operations from this sync worker function
    result = asyncio.run(
        _async_ingest(
            site_id=site_id,
            modality=modality,
            payload_key=payload_key,
            tenant_id=tenant_id,
            actor_id=actor_id,
            blob_endpoint_url=_blob_endpoint,
            blob_bucket=_blob_bucket,
            blob_access_key=_blob_access_key,
            blob_secret_key=_blob_secret_key,
            mongo_url=_mongo_url,
        )
    )

    # D-06: worker opens its OWN session and commits the "ingest:completed" audit event.
    # append_audit never commits (D-05) — the worker owns the commit here.
    from veridoc_audit import AuditEvent, append_audit

    with _session_scope(_db_url) as session:
        append_audit(
            session,
            AuditEvent(
                actor_id=actor_id,
                actor_role="ingestion-service",
                tenant_id=tenant_id,
                action="ingest:completed",
                entity_type="ingest-batch",
                entity_id=payload_key,
                before=None,
                after={
                    "site_id": site_id,
                    "modality": modality,
                    "resource_ids": result["resource_ids"],
                    "provenance_id": result["provenance_id"],
                },
                occurred_at=datetime.now(UTC),
            ),
        )
        session.commit()  # worker owns the commit (D-06 deviation from Phase 1 default)

    return result
