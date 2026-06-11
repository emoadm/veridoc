"""Test fixtures for veridoc-fhir integration tests.

Provides an ephemeral MongoDB for repository integration tests.
Database resolution order:

1. ``VERIDOC_TEST_MONGODB_URL`` env var — a real local MongoDB (e.g. the CI service
   container or a developer's local mongod). This is the primary path on hosts without
   Docker (testcontainers needs a Docker daemon).
2. ``testcontainers`` — spins an ephemeral ``mongo:7-jammy`` container when Docker is
   available (Wave 0 default).

If neither is available the DB-backed tests are skipped with a clear reason (the pure
unit tests — model construction, JSON round-trip — still run).

Mirrors ``libs/veridoc-audit/tests/conftest.py`` three-path resolution pattern exactly,
substituting PostgresContainer with MongoDbContainer and the appropriate env var.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def mongo_url():
    """Resolve a MongoDB URL (env var first, then testcontainers) or skip DB-backed tests."""
    env_url = os.environ.get("VERIDOC_TEST_MONGODB_URL")
    if env_url:
        yield env_url
        return

    # Fall back to testcontainers (needs a running Docker daemon).
    try:
        from testcontainers.mongodb import MongoDbContainer
    except Exception:  # pragma: no cover - import guard
        pytest.skip("no VERIDOC_TEST_MONGODB_URL and testcontainers unavailable")

    try:
        container = MongoDbContainer("mongo:7-jammy")
        container.start()
    except Exception as exc:  # pragma: no cover - Docker absent
        pytest.skip(f"no VERIDOC_TEST_MONGODB_URL and Docker unavailable: {exc}")

    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest.fixture()
def clean_fhir_collection(mongo_url: str):
    """Drop the fhir_resources collection before each test for isolation.

    Function-scoped: ensures each test starts with a clean collection state.
    Mirrors the ``migrated_engine`` pattern from veridoc-audit (per-test teardown).

    Usage::

        async def test_save_patient(clean_fhir_collection, mongo_url):
            repo = FhirRepository(mongo_url=mongo_url)
            # collection is empty at start of test
    """
    from pymongo import MongoClient

    client = MongoClient(mongo_url)
    db = client["veridoc_fhir"]
    db.drop_collection("fhir_resources")
    yield
    db.drop_collection("fhir_resources")
    client.close()
