"""Integration test: RQ worker ingest_job → FHIR resources in MongoDB + audit event.

RED phase — tests fail until worker.py is implemented in libs/veridoc-ingestion.

Tests:
1. ingest_job loads bytes from blob by payload_key, runs adapter, persists FHIR resources
   + Provenance to Mongo, and commits an "ingest:completed" audit event.
2. make_queue returns a Queue with JSONSerializer.
3. ingest_job args are JSON-serializable primitives (no raw bytes).
4. After a job, FHIR resources for the patient are queryable in MongoDB.

Docker required for Mongo + Postgres + MinIO testcontainers — tests skip cleanly without it.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest


# ---------------------------------------------------------------------------
# Fixtures: MongoDB (Mongo testcontainer or env var)
# ---------------------------------------------------------------------------

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


def _normalize_pg_url(url: str) -> str:
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@pytest.fixture(scope="session")
def db_url():
    env_url = os.environ.get("VERIDOC_TEST_DATABASE_URL")
    if env_url:
        yield _normalize_pg_url(env_url)
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
        yield _normalize_pg_url(container.get_connection_url())
    finally:
        container.stop()


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
    try:
        container = MinioContainer()
        container.start()
    except Exception as exc:
        pytest.skip(f"no VERIDOC_TEST_MINIO_URL and Docker unavailable: {exc}")
    try:
        yield container.get_url()
    finally:
        container.stop()


@pytest.fixture(scope="session")
def pg_engine(db_url):
    from sqlalchemy import create_engine, text
    eng = create_engine(db_url, future=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"cannot connect to test Postgres at {db_url}: {exc}")
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def migrated_engine(pg_engine):
    """Apply audit + subject migrations for the worker audit write."""
    from reference_service.migrate import apply_all, revert_all

    with pg_engine.begin() as conn:
        revert_all(conn)
        apply_all(conn)
    yield pg_engine
    with pg_engine.begin() as conn:
        revert_all(conn)


@pytest.fixture(autouse=True)
def _fresh_keystore():
    os.environ.setdefault("VERIDOC_MASTER_KEY", "00" * 32)
    from veridoc_crypto.keys import reset_keystore
    reset_keystore()
    yield
    reset_keystore()


# ---------------------------------------------------------------------------
# Helpers: Synthea fixture loader
# ---------------------------------------------------------------------------

def _load_synthea_bundle() -> bytes:
    """Load a Synthea R4B bundle fixture for testing."""
    from pathlib import Path
    fixtures_dir = Path(__file__).resolve().parents[4] / "libs" / "veridoc-fhir" / "tests" / "fixtures" / "fhir"
    bundles = list(fixtures_dir.glob("*.json"))
    if not bundles:
        pytest.skip("no Synthea fixtures found in libs/veridoc-fhir/tests/fixtures/fhir/")
    return bundles[0].read_bytes()


def _setup_minio_bucket(endpoint: str) -> tuple[str, str, str]:
    """Create the test bucket in MinIO; return (bucket, access_key, secret_key)."""
    import boto3
    access_key = "minioadmin"
    secret_key = "minioadmin"
    bucket = "veridoc-test-docs"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)
    return bucket, access_key, secret_key


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_make_queue_uses_json_serializer():
    """make_queue(redis_url) must use JSONSerializer (Pitfall 3 / T-02-SVC-03)."""
    import inspect
    from veridoc_ingestion.worker import make_queue
    src = inspect.getsource(make_queue)
    assert "JSONSerializer" in src, "make_queue must pass serializer=JSONSerializer to Queue()"


def test_ingest_job_args_are_json_serializable():
    """ingest_job signature must use only JSON-serializable arg types (Pitfall 4)."""
    import inspect
    from veridoc_ingestion.worker import ingest_job
    src = inspect.getsource(ingest_job)
    # payload_key must be a string, NOT bytes
    assert "payload_key" in src, "ingest_job must accept payload_key (string blob key)"
    # raw bytes anti-pattern should not be present as the primary data transport
    assert "payload: bytes" not in src, "ingest_job must not accept raw bytes directly"


def test_ingest_job_has_audit_commit():
    """ingest_job must call append_audit + session.commit() (D-06 deviation)."""
    import inspect
    from veridoc_ingestion.worker import ingest_job
    src = inspect.getsource(ingest_job)
    assert "append_audit" in src, "ingest_job must call append_audit (D-06)"
    assert "commit" in src, "ingest_job must commit its own session (D-06 deviation)"


def test_ingest_job_end_to_end(mongo_url, migrated_engine, minio_endpoint):
    """Full end-to-end: ingest_job → FHIR resources in MongoDB + audit row in Postgres.

    Skips when Docker is unavailable (Mongo/Postgres/MinIO testcontainers absent).
    """
    import asyncio
    from sqlalchemy.orm import sessionmaker
    from veridoc_ingestion.worker import ingest_job
    from veridoc_ingestion.registry import SourceProfileRegistry
    from veridoc_ingestion.adapter import SourceProfile, SourceModality
    from veridoc_fhir.repository import FhirRepository

    # Set up blob store + upload fixture payload
    bundle_bytes = _load_synthea_bundle()
    bucket, access_key, secret_key = _setup_minio_bucket(minio_endpoint)
    site_id = "site-test-001"
    payload_key = f"{site_id}/{uuid.uuid4()}.json"

    import boto3
    s3 = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    s3.put_object(Bucket=bucket, Key=payload_key, Body=bundle_bytes, ContentType="application/json")

    # Register source profile in env for the worker to discover
    os.environ["VERIDOC_BLOB_ENDPOINT_URL"] = minio_endpoint
    os.environ["VERIDOC_BLOB_BUCKET"] = bucket
    os.environ["VERIDOC_BLOB_ACCESS_KEY"] = access_key
    os.environ["VERIDOC_BLOB_SECRET_KEY"] = secret_key
    os.environ["VERIDOC_MONGODB_URL"] = mongo_url
    os.environ["VERIDOC_DATABASE_URL"] = str(migrated_engine.url)

    # Call ingest_job directly (synchronous call — no Redis broker needed)
    result = ingest_job(
        site_id=site_id,
        modality="native-fhir",
        payload_key=payload_key,
        tenant_id="test-site/test-study",
        actor_id="test-service-account",
        blob_endpoint_url=minio_endpoint,
        blob_bucket=bucket,
        blob_access_key=access_key,
        blob_secret_key=secret_key,
        mongo_url=mongo_url,
        db_url=str(migrated_engine.url),
    )

    # Result must be a JSON-serializable dict with resource_ids
    assert isinstance(result, dict), f"ingest_job must return dict, got {type(result)}"
    assert "resource_ids" in result, f"result must contain resource_ids, got {result}"
    assert len(result["resource_ids"]) > 0, "at least one resource must be persisted"
    assert "provenance_id" in result, "result must contain provenance_id"

    # Verify FHIR resources are in MongoDB
    repo = FhirRepository(mongo_url=mongo_url)
    # Find Patient resources (at least one must be present after ingest)
    patients = asyncio.run(repo.find_by_patient.__func__(repo, "", "Patient"))  # type: ignore[attr-defined]
    # Since find_by_patient uses subject.reference, query raw
    async def _count_patients():
        cursor = repo._col.find({"resourceType": "Patient"})
        return await cursor.to_list(length=None)
    patients = asyncio.run(_count_patients())
    assert len(patients) > 0, "At least one Patient resource must be in MongoDB after ingest"
    repo.close()

    # Verify audit event in Postgres
    from sqlalchemy import text as sa_text
    factory = sessionmaker(bind=migrated_engine, future=True)
    session = factory()
    try:
        rows = session.execute(
            sa_text("SELECT action FROM audit_log WHERE action = 'ingest:completed' LIMIT 5")
        ).fetchall()
        assert len(rows) > 0, "ingest:completed audit row must be present in audit_log"
    finally:
        session.close()
