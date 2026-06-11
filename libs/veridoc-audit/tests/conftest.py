"""Test fixtures for the DB-backed audit tests.

Provides an ephemeral Postgres for the integration tests (tamper-detection, same-txn).
Database resolution order:

1. ``VERIDOC_TEST_DATABASE_URL`` env var — a real local Postgres (e.g. the CI service
   container or a developer's local cluster). This is the primary path on hosts without
   Docker (testcontainers needs a Docker daemon).
2. ``testcontainers`` — spins an ephemeral ``postgres`` container when Docker is available
   (VALIDATION Wave 0 default).

If neither is available the DB-backed tests are skipped with a clear reason (the pure
unit tests in test_jcs_golden / test_chain still run). The migration is applied to a fresh
schema and the ``audit_log`` table is truncated/rebuilt per test for isolation.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Load the migration module by path (migrations/ is not an installed package on sys.path).
_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "0001_audit_log.py"
_spec = importlib.util.spec_from_file_location("audit_migration_0001", _MIGRATION_PATH)
migration = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(migration)


def _normalize_url(url: str) -> str:
    """Force the psycopg (v3) driver so the binary wheel is used.

    testcontainers' ``get_connection_url()`` yields a ``postgresql+psycopg2://`` URL and
    env-var URLs may use a bare ``postgresql://`` — both must resolve to psycopg v3, else
    SQLAlchemy tries to import the (uninstalled) psycopg2 driver.
    """
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


@pytest.fixture(scope="session")
def db_url():
    """Resolve a Postgres URL (env var first, then testcontainers) or skip DB-backed tests."""
    env_url = os.environ.get("VERIDOC_TEST_DATABASE_URL")
    if env_url:
        yield _normalize_url(env_url)
        return

    # Fall back to testcontainers (needs a running Docker daemon).
    try:
        from testcontainers.postgres import PostgresContainer
    except Exception:  # pragma: no cover - import guard
        pytest.skip("no VERIDOC_TEST_DATABASE_URL and testcontainers unavailable")

    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:  # pragma: no cover - Docker absent
        pytest.skip(f"no VERIDOC_TEST_DATABASE_URL and Docker unavailable: {exc}")

    try:
        yield _normalize_url(container.get_connection_url())
    finally:
        container.stop()


@pytest.fixture(scope="session")
def engine(db_url: str):
    eng = create_engine(db_url, future=True)
    # Verify connectivity early with a clear skip if the server is unreachable.
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"cannot connect to test Postgres at {db_url}: {exc}")
    yield eng
    eng.dispose()


@pytest.fixture()
def migrated_engine(engine):
    """Apply the migration to a clean schema; tear it down afterward (per-test isolation)."""
    with engine.begin() as conn:
        migration.revert(conn)  # drop any leftovers from a prior run
        migration.apply(conn)
    yield engine
    with engine.begin() as conn:
        migration.revert(conn)


@pytest.fixture()
def session(migrated_engine) -> Session:
    """A SQLAlchemy Session bound to the migrated test database.

    The caller controls the transaction boundary (commit/rollback) exactly as a real
    business handler would — append_audit never commits on its own (D-05).
    """
    maker = sessionmaker(bind=migrated_engine, future=True)
    sess = maker()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()
