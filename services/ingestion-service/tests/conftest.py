"""Integration-test fixtures for the ingestion-service (plan 02-06).

Cloned from ``services/reference-service/tests/conftest.py`` (exact analog in
02-PATTERNS.md) and extended with:
- MongoDB testcontainer fixture (``mongo_url``).
- MinIO testcontainer fixture (``minio_endpoint``).
- Blob store helpers.

The authentication fixtures (``keypair``, ``jwks``, ``mint_token``, ``make_token``)
are identical to the reference-service conftest — same realm contract (RS256/MFA,
8 roles, site/study claims) but with AUDIENCE = "ingestion-service".

Database resolution (three-path, mirroring 01-02/01-03/01-04 pattern):
1. ``VERIDOC_TEST_DATABASE_URL`` env var — a real local Postgres.
2. ``testcontainers`` — ephemeral Postgres when Docker is available.
3. otherwise DB-backed tests skip cleanly.

MongoDB resolution (same three-path):
1. ``VERIDOC_TEST_MONGODB_URL`` env var.
2. ``testcontainers`` — ephemeral ``mongo:7-jammy`` when Docker is available.
3. otherwise Mongo-backed tests skip cleanly.

MinIO resolution (same three-path):
1. ``VERIDOC_TEST_MINIO_URL`` env var.
2. ``testcontainers`` — ephemeral MinioContainer when Docker is available.
3. otherwise MinIO-backed tests skip cleanly.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, text
from veridoc_auth import JWKSCache
from veridoc_crypto.keys import reset_keystore

_REPO_ROOT = Path(__file__).resolve().parents[4]
_REALM_PATH = _REPO_ROOT / "deploy" / "keycloak" / "veridoc-realm.json"
_TEST_USERS_PATH = _REPO_ROOT / "deploy" / "keycloak" / "test-users.json"

# Realm contract — audience is "ingestion-service" (not "reference-service")
ISSUER = "https://kc.veridoc.local/realms/veridoc"
AUDIENCE = "ingestion-service"
KID = "ingestion-service-test-key"


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Force the psycopg (v3) driver prefix."""
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


# ---------------------------------------------------------------------------
# Postgres (audit chain)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_url():
    env_url = os.environ.get("VERIDOC_TEST_DATABASE_URL")
    if env_url:
        yield _normalize_url(env_url)
        return
    try:
        from testcontainers.postgres import PostgresContainer
    except Exception:  # pragma: no cover
        pytest.skip("no VERIDOC_TEST_DATABASE_URL and testcontainers unavailable")
    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"no VERIDOC_TEST_DATABASE_URL and Docker unavailable: {exc}")
    try:
        yield _normalize_url(container.get_connection_url())
    finally:
        container.stop()


@pytest.fixture(scope="session")
def engine(db_url: str):
    eng = create_engine(db_url, future=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"cannot connect to test Postgres at {db_url}: {exc}")
    yield eng
    eng.dispose()


@pytest.fixture()
def migrated_engine(engine):
    """Apply BOTH migrations (audit_log + subject) to a clean schema."""
    from reference_service.migrate import apply_all, revert_all
    with engine.begin() as conn:
        revert_all(conn)
        apply_all(conn)
    yield engine
    with engine.begin() as conn:
        revert_all(conn)


# ---------------------------------------------------------------------------
# MongoDB (FHIR document store)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def mongo_url():
    env_url = os.environ.get("VERIDOC_TEST_MONGODB_URL")
    if env_url:
        yield env_url
        return
    try:
        from testcontainers.mongodb import MongoDbContainer
    except Exception:  # pragma: no cover
        pytest.skip("no VERIDOC_TEST_MONGODB_URL and testcontainers unavailable")
    try:
        container = MongoDbContainer("mongo:7-jammy")
        container.start()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"no VERIDOC_TEST_MONGODB_URL and Docker unavailable: {exc}")
    try:
        yield container.get_connection_url()
    finally:
        container.stop()


# ---------------------------------------------------------------------------
# MinIO (blob store for retained originals)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def minio_endpoint():
    """Resolve a MinIO endpoint URL or skip.

    Returns the HTTP endpoint URL (e.g. ``http://localhost:9000``).
    """
    env_url = os.environ.get("VERIDOC_TEST_MINIO_URL")
    if env_url:
        yield env_url
        return
    try:
        from testcontainers.minio import MinioContainer
    except Exception:  # pragma: no cover
        pytest.skip("no VERIDOC_TEST_MINIO_URL and testcontainers unavailable")
    try:
        container = MinioContainer()
        container.start()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"no VERIDOC_TEST_MINIO_URL and Docker unavailable: {exc}")
    try:
        yield container.get_url()
    finally:
        container.stop()


# ---------------------------------------------------------------------------
# Crypto keystore isolation (per-test)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_keystore():
    os.environ.setdefault("VERIDOC_MASTER_KEY", "00" * 32)
    reset_keystore()
    yield
    reset_keystore()


# ---------------------------------------------------------------------------
# App + auth
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def jwks(keypair) -> JWKSCache:
    return JWKSCache.from_public_keys({KID: keypair.public_key()})


def mint_token(keypair, *, sub, roles, site, study, mfa=True, **overrides) -> str:
    """Mint a real RS256 access token mirroring a Keycloak token for the realm contract."""
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": sub,
        "exp": now + 300,
        "iat": now,
        "acr": "mfa" if mfa else "password",
        "amr": ["pwd", "otp"] if mfa else ["pwd"],
        "realm_access": {"roles": list(roles)},
        "site": site,
        "study": study,
    }
    claims.update(overrides)
    return jwt.encode(claims, keypair, algorithm="RS256", headers={"kid": KID})


@pytest.fixture()
def make_token(keypair):
    """A token-minting helper bound to the test keypair (real RS256, realm contract)."""

    def _make(*, sub, roles, site, study, mfa=True, **overrides) -> str:
        return mint_token(keypair, sub=sub, roles=roles, site=site, study=study, mfa=mfa, **overrides)

    return _make


@pytest.fixture()
def app(migrated_engine, jwks):
    """Build the FastAPI app bound to the migrated test DB + in-test JWKS."""
    from ingestion_service.main import create_app
    return create_app(engine=migrated_engine, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
