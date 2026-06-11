"""Integration tests for POST /ingest/{site_id} — the authenticated async ingest endpoint.

RED phase — tests fail until the ingestion-service config/main/api are implemented.

Covers:
- 202 + job_id returned for a permitted role (site-coordinator, data-manager)
- 401 for unauthenticated requests
- 403 for wrong role
- 401 for missing/unresolvable tenant (fail-closed tenancy)
- "ingest:enqueued" audit row written same-transaction
- main.py lifespan creates MongoDB indexes + RQ Queue with JSONSerializer

Docker (Postgres testcontainer) required for audit tests — skip cleanly without it.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

_REPO_ROOT = Path(__file__).resolve().parents[4]
_REALM_PATH = _REPO_ROOT / "deploy" / "keycloak" / "veridoc-realm.json"

ISSUER = "https://kc.veridoc.local/realms/veridoc"
AUDIENCE = "ingestion-service"
KID = "ingestion-service-test-key"


# ---------------------------------------------------------------------------
# Database fixtures (Postgres testcontainer or env var)
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


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


@pytest.fixture(scope="session")
def engine(db_url: str):
    from sqlalchemy import create_engine, text
    eng = create_engine(db_url, future=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"cannot connect to test Postgres at {db_url}: {exc}")
    yield eng
    eng.dispose()


@pytest.fixture()
def migrated_engine(engine):
    """Apply audit + subject migrations (reference_service.migrate) to a clean schema."""
    from reference_service.migrate import apply_all, revert_all
    with engine.begin() as conn:
        revert_all(conn)
        apply_all(conn)
    yield engine
    with engine.begin() as conn:
        revert_all(conn)


# ---------------------------------------------------------------------------
# Crypto keystore isolation
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_keystore():
    os.environ.setdefault("VERIDOC_MASTER_KEY", "00" * 32)
    from veridoc_crypto.keys import reset_keystore
    reset_keystore()
    yield
    reset_keystore()


# ---------------------------------------------------------------------------
# Auth fixtures (real RS256 tokens, no live Keycloak)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def jwks(keypair):
    from veridoc_auth import JWKSCache
    return JWKSCache.from_public_keys({KID: keypair.public_key()})


def mint_token(keypair, *, sub, roles, site, study, mfa=True, **overrides) -> str:
    """Mint a real RS256 access token (realm-contract clone from reference-service conftest)."""
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
    def _make(*, sub, roles, site, study, mfa=True, **overrides) -> str:
        return mint_token(keypair, sub=sub, roles=roles, site=site, study=study, mfa=mfa, **overrides)
    return _make


# ---------------------------------------------------------------------------
# App fixture (ingestion-service create_app wired to test DB + test JWKS)
# ---------------------------------------------------------------------------

def _test_settings():
    """Settings with site-001 registered as a native-fhir source (CR-04 routing)."""
    from ingestion_service.config import Settings
    return Settings(site_modalities={"site-001": "native-fhir"})


@pytest.fixture()
def app(migrated_engine, jwks):
    """FastAPI app bound to migrated test DB + in-process JWKS. No Redis needed for unit tests."""
    from ingestion_service.main import create_app
    return create_app(
        engine=migrated_engine,
        jwks=jwks,
        issuer=ISSUER,
        audience=AUDIENCE,
        settings=_test_settings(),
    )


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient
    # lifespan=True would start MongoDB + Redis in tests; use lifespan=False for unit tests
    # (the queue is not tested at this level — the enqueue unit is mocked or skipped)
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_post_ingest_202_permitted_role(client, make_token):
    """POST /ingest/site-001 with site-coordinator role → 202 + job_id."""
    token = make_token(sub="user-1", roles=["site-coordinator"], site="site-001", study="study-A")
    payload = b'{"resourceType": "Bundle", "type": "transaction", "entry": []}'
    resp = client.post(
        "/ingest/site-001",
        content=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "job_id" in data, f"Response must include job_id, got: {data}"


def test_post_ingest_202_data_manager(client, make_token):
    """POST /ingest/site-001 with data-manager role → 202."""
    token = make_token(sub="user-2", roles=["data-manager"], site="site-001", study="study-A")
    payload = b'{"resourceType": "Bundle", "type": "transaction", "entry": []}'
    resp = client.post(
        "/ingest/site-001",
        content=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 202


def test_post_ingest_401_unauthenticated(client):
    """POST /ingest/site-001 without Authorization → 401."""
    resp = client.post(
        "/ingest/site-001",
        content=b"test",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401


def test_post_ingest_403_wrong_role(client, make_token):
    """POST /ingest/site-001 with regulatory-affairs role → 403 (deny-by-default RBAC)."""
    token = make_token(sub="user-3", roles=["regulatory-affairs"], site="site-001", study="study-A")
    resp = client.post(
        "/ingest/site-001",
        content=b"test",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 403


def test_post_ingest_401_missing_tenant(client, keypair):
    """POST /ingest/site-001 with no site/study claims → 401 (fail-closed tenancy)."""
    # Token with NO site/study claims → tenant_from_claims raises TenancyError → 401
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-4",
        "exp": now + 300,
        "iat": now,
        "acr": "mfa",
        "amr": ["pwd", "otp"],
        "realm_access": {"roles": ["site-coordinator"]},
        # No "site" or "study" claims — fail-closed tenancy must reject this
    }
    token = jwt.encode(claims, keypair, algorithm="RS256", headers={"kid": KID})
    resp = client.post(
        "/ingest/site-001",
        content=b"test",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401


def test_post_ingest_enqueued_audit_event(migrated_engine, jwks, make_token):
    """POST /ingest/site-001 writes an 'ingest:enqueued' audit row same-transaction."""
    from sqlalchemy import text as sa_text
    from sqlalchemy.orm import sessionmaker
    from ingestion_service.main import create_app
    from fastapi.testclient import TestClient

    app = create_app(
        engine=migrated_engine, jwks=jwks, issuer=ISSUER, audience=AUDIENCE,
        settings=_test_settings(),
    )
    token = make_token(sub="audit-user", roles=["site-coordinator"], site="site-001", study="study-A")
    payload = b'{"resourceType": "Bundle", "type": "transaction", "entry": []}'

    with TestClient(app) as client:
        resp = client.post(
            "/ingest/site-001",
            content=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
    assert resp.status_code == 202

    # Check that an 'ingest:enqueued' audit row exists in audit_log
    factory = sessionmaker(bind=migrated_engine, future=True)
    session = factory()
    try:
        rows = session.execute(
            sa_text(
                "SELECT action, entity_type FROM audit_log WHERE action = 'ingest:enqueued' LIMIT 5"
            )
        ).fetchall()
        assert len(rows) > 0, "ingest:enqueued audit row must be present after POST /ingest"
        assert rows[0].entity_type == "ingest-request"
    finally:
        session.close()


def test_main_py_has_json_serializer():
    """main.py lifespan must initialize an RQ Queue with JSONSerializer (Pitfall 3)."""
    import inspect
    from ingestion_service.main import create_app
    src = inspect.getsource(create_app)
    assert "JSONSerializer" in src, "main.py create_app must use JSONSerializer for the RQ queue"


def test_main_py_has_create_indexes():
    """main.py must call create_indexes() at startup (Pitfall 6)."""
    import inspect
    from ingestion_service.main import create_app
    src = inspect.getsource(create_app)
    assert "create_indexes" in src, "main.py must call create_indexes() at startup (Pitfall 6)"


def test_ingest_api_has_require_write_role():
    """ingest.py must define/use require_write_role (deny-by-default RBAC)."""
    import inspect
    import ingestion_service.api.ingest as ingest_mod
    src = inspect.getsource(ingest_mod)
    assert "require_write_role" in src
