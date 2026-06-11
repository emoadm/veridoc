"""Test fixtures for veridoc-ingestion integration tests.

Provides ephemeral MinIO (S3-compatible blob store) for blob-store integration tests
and a fakeredis/eager-RQ helper for synchronous worker-function tests.

Resolution order:

1. ``VERIDOC_TEST_MINIO_URL`` env var — a real local MinIO or S3-compatible endpoint.
2. ``testcontainers`` — spins an ephemeral ``minio/minio`` container when Docker
   is available (Wave 0 default).

If neither is available the MinIO-backed tests are skipped with a clear reason.

Mirrors ``libs/veridoc-audit/tests/conftest.py`` three-path resolution pattern, analogous
to ``libs/veridoc-fhir/tests/conftest.py``, substituting MinioContainer.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def minio_endpoint():
    """Resolve a MinIO endpoint URL (env var first, then testcontainers) or skip.

    Returns the HTTP endpoint URL (e.g. ``http://localhost:9000``), NOT an
    s3:// URI. Pass to ``S3BlobStore(endpoint_url=minio_endpoint, ...)``.
    """
    env_url = os.environ.get("VERIDOC_TEST_MINIO_URL")
    if env_url:
        yield env_url
        return

    # Fall back to testcontainers (needs a running Docker daemon).
    try:
        from testcontainers.minio import MinioContainer
    except Exception:  # pragma: no cover - import guard
        pytest.skip("no VERIDOC_TEST_MINIO_URL and testcontainers unavailable")

    try:
        container = MinioContainer()
        container.start()
    except Exception as exc:  # pragma: no cover - Docker absent
        pytest.skip(f"no VERIDOC_TEST_MINIO_URL and Docker unavailable: {exc}")

    try:
        # MinioContainer exposes get_url() → http://host:port
        yield container.get_url()
    finally:
        container.stop()


@pytest.fixture()
def eager_rq_queue():
    """A synchronous (eager) RQ queue for testing worker functions without a broker.

    Uses an in-process connection so RQ jobs execute synchronously in the test process.
    Eliminates the need for a real Redis daemon in unit tests; uses fakeredis when
    available, otherwise creates a real Queue with is_async=False.

    Usage::

        def test_ingest_job_success(eager_rq_queue):
            from veridoc_ingestion.worker import ingest_job
            job = eager_rq_queue.enqueue(ingest_job, site_id='site-001', ...)
            assert job.result is not None
    """
    try:
        import fakeredis
        from rq import Queue
        from rq.serializers import JSONSerializer

        conn = fakeredis.FakeRedis()
        yield Queue(connection=conn, is_async=False, serializer=JSONSerializer)
    except ImportError:
        # fakeredis not installed — fall back to a real sync Queue using Queue(is_async=False)
        # This requires Redis to be reachable; skip if not.
        try:
            from redis import Redis
            from rq import Queue
            from rq.serializers import JSONSerializer

            conn = Redis()
            conn.ping()
            yield Queue(connection=conn, is_async=False, serializer=JSONSerializer)
        except Exception as exc:  # pragma: no cover - Redis absent
            pytest.skip(f"fakeredis unavailable and no local Redis: {exc}")
