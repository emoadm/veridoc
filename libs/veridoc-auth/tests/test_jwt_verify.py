"""OIDC access-token verification against a JWKS (Keycloak shape) — T-04-01 / T-04-02.

These tests use a locally generated RSA keypair and an in-test JWKS (no live Keycloak —
that round-trip is plan 01-05). They prove the API-tier security invariants:

- a well-formed, correctly-signed, MFA-bearing token is ACCEPTED and yields a Principal;
- bad signature / ``alg=none`` / wrong issuer / wrong audience / expired are REJECTED (401);
- a token missing the MFA acr/amr claim is REJECTED (MFA bypass blocked).
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from veridoc_auth import (
    AuthError,
    JWKSCache,
    Principal,
    verify_token,
)

ISSUER = "https://kc.veridoc.local/realms/veridoc"
AUDIENCE = "reference-service"
KID = "test-key-1"


@pytest.fixture(scope="module")
def keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def jwks(keypair) -> JWKSCache:
    """An in-test JWKS cache holding our single public key (no network fetch)."""
    return JWKSCache.from_public_keys({KID: keypair.public_key()})


def _make_token(keypair, *, claims_override=None, alg="RS256", headers=None) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-123",
        "exp": now + 300,
        "iat": now,
        "acr": "mfa",
        "amr": ["pwd", "otp"],
        "realm_access": {"roles": ["cra"]},
        "site": "site-001",
        "study": "study-A",
    }
    if claims_override:
        claims = {**claims, **claims_override}
    hdrs = {"kid": KID}
    if headers:
        hdrs.update(headers)
    if alg == "none":
        # Build an unsigned alg=none token by hand (PyJWT refuses to *sign* none).
        return jwt.encode(claims, key="", algorithm="none", headers={"kid": KID})
    return jwt.encode(claims, keypair, algorithm=alg, headers=hdrs)


def test_valid_mfa_token_is_accepted(keypair, jwks):
    token = _make_token(keypair)
    principal = verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)
    assert isinstance(principal, Principal)
    assert principal.subject == "user-123"
    assert "cra" in principal.roles
    assert principal.acr == "mfa"
    assert principal.tenant_claims == {"site": "site-001", "study": "study-A"}


def test_bad_signature_is_rejected(jwks):
    # Sign with a DIFFERENT key than the JWKS holds.
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_token(other)
    with pytest.raises(AuthError):
        verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


def test_alg_none_is_rejected(keypair, jwks):
    token = _make_token(keypair, alg="none")
    with pytest.raises(AuthError):
        verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


def test_wrong_issuer_is_rejected(keypair, jwks):
    token = _make_token(keypair, claims_override={"iss": "https://evil.example/realms/x"})
    with pytest.raises(AuthError):
        verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


def test_wrong_audience_is_rejected(keypair, jwks):
    token = _make_token(keypair, claims_override={"aud": "some-other-client"})
    with pytest.raises(AuthError):
        verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


def test_expired_token_is_rejected(keypair, jwks):
    now = int(time.time())
    token = _make_token(keypair, claims_override={"exp": now - 10, "iat": now - 600})
    with pytest.raises(AuthError):
        verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


def test_token_without_mfa_acr_is_rejected(keypair, jwks):
    # No acr=mfa and no otp in amr => MFA bypass attempt.
    token = _make_token(
        keypair, claims_override={"acr": "password", "amr": ["pwd"]}
    )
    with pytest.raises(AuthError):
        verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


def test_mfa_via_amr_otp_is_accepted(keypair, jwks):
    # acr absent but amr contains otp => MFA was performed; accept.
    token = _make_token(
        keypair, claims_override={"acr": None, "amr": ["pwd", "otp"]}
    )
    principal = verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)
    assert "otp" in principal.amr


def test_unknown_kid_is_rejected(keypair, jwks):
    token = _make_token(keypair, headers={"kid": "no-such-kid"})
    with pytest.raises(AuthError):
        verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)


def test_rs256_is_pinned_hs256_rejected(keypair, jwks):
    """An HS256 token (symmetric) must be rejected — algorithm confusion / pin RS256."""
    token = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": "x", "acr": "mfa"},
        key="public-key-as-hmac-secret",
        algorithm="HS256",
        headers={"kid": KID},
    )
    with pytest.raises(AuthError):
        verify_token(token, jwks=jwks, issuer=ISSUER, audience=AUDIENCE)
