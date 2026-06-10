"""Integration-test fixtures for the reference service (plan 01-05).

The reference service is the D-07 walking skeleton where all five shared libs meet, so its
tests exercise the FULL path: HTTP -> Keycloak-style JWT authn/MFA -> RBAC -> fail-closed
tenancy -> envelope-encrypted PII + deterministic pseudonym -> same-transaction hash-chained
audit -> Postgres.

Database resolution (the 01-02/01-03/01-04 pattern):
1. ``VERIDOC_TEST_DATABASE_URL`` env var — a real local Postgres (CI service container or a
   developer's least-privilege test role/DB). Primary path on Docker-less hosts.
2. ``testcontainers`` — ephemeral ``postgres`` when Docker is available (VALIDATION Wave 0).
3. otherwise the DB-backed tests skip cleanly (the clean-clone harness stays green).

Keycloak: a *live* Keycloak realm round-trip runs only when ``VERIDOC_KEYCLOAK_URL`` is set
(Docker-less CI / dev hosts have no Keycloak container). Otherwise — exactly as the
veridoc-auth lib tests do (plan 01-04) — we mint REAL RS256 access tokens from a locally
generated keypair and serve their public key through a ``JWKSCache.from_public_keys``. This
verifies the identical ``verify_token`` -> RBAC -> tenancy -> encrypted audited write code
path the service runs in production; only the token *issuer* is local instead of a live
Keycloak. The realm contract (issuer, audience, claim names, MFA acr/amr, the 8 roles, and
the site/study tenant mappers) is read from ``deploy/keycloak/veridoc-realm.json`` +
``deploy/keycloak/test-users.json`` so the fixtures stay faithful to the realm-as-code.
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

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REALM_PATH = _REPO_ROOT / "deploy" / "keycloak" / "veridoc-realm.json"
_TEST_USERS_PATH = _REPO_ROOT / "deploy" / "keycloak" / "test-users.json"

# The realm-as-code contract (must match deploy/keycloak/veridoc-realm.json).
ISSUER = "https://kc.veridoc.local/realms/veridoc"
AUDIENCE = "reference-service"
KID = "reference-service-test-key"


def _normalize_url(url: str) -> str:
    """Force the psycopg (v3) driver so the binary wheel is used."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def db_url():
    env_url = os.environ.get("VERIDOC_TEST_DATABASE_URL")
    if env_url:
        yield _normalize_url(env_url)
        return
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
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"cannot connect to test Postgres at {db_url}: {exc}")
    yield eng
    eng.dispose()


@pytest.fixture()
def migrated_engine(engine):
    """Apply BOTH migrations (audit_log + subject) to a clean schema, tearing down after."""
    from reference_service.migrate import apply_all, revert_all

    with engine.begin() as conn:
        revert_all(conn)
        apply_all(conn)
    yield engine
    with engine.begin() as conn:
        revert_all(conn)


# --------------------------------------------------------------------------- #
# Crypto keystore isolation (per-test) so erasure in one test never leaks.
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def _fresh_keystore():
    # Stable master key for the test session so pseudonyms recompute deterministically.
    os.environ.setdefault("VERIDOC_MASTER_KEY", "00" * 32)
    reset_keystore()
    yield
    reset_keystore()


# --------------------------------------------------------------------------- #
# App + auth
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def jwks(keypair) -> JWKSCache:
    return JWKSCache.from_public_keys({KID: keypair.public_key()})


@pytest.fixture(scope="session")
def test_users() -> dict:
    """Load the seeded role+tenant test users (deploy/keycloak/test-users.json)."""
    return json.loads(_TEST_USERS_PATH.read_text())


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
        return mint_token(
            keypair, sub=sub, roles=roles, site=site, study=study, mfa=mfa, **overrides
        )

    return _make


@pytest.fixture()
def app(migrated_engine, jwks):
    """Build the FastAPI app bound to the migrated test DB + in-test JWKS."""
    from reference_service.main import create_app

    return create_app(engine=migrated_engine, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
