"""OIDC authn middleware: JWKS signature verify + iss/aud/exp + MFA acr enforcement.

RESEARCH Pattern 2 / Anti-Patterns / Code Examples. The API tier NEVER handles
credentials — Keycloak owns auth/MFA/sessions (D-01); this only *validates* the resulting
access token:

1. resolve the signing key by the token's ``kid`` from the JWKS (no key in JWKS => reject);
2. decode with ``algorithms=["RS256"]`` pinned — ``alg=none`` and HS256 are rejected
   (algorithm-confusion / unsigned-token bypass, T-04-01);
3. verify ``iss`` / ``aud`` / ``exp`` (and ``iat``);
4. assert the MFA claim: ``acr`` indicates MFA **or** ``amr`` contains ``otp`` — a token
   without MFA is rejected (T-04-02), enforcing MFA in the API tier, not just Keycloak.

On success it returns a :class:`Principal` (subject, realm roles, site/study tenant claims,
acr/amr) which downstream RBAC + tenancy consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import jwt

from .errors import AuthError
from .jwks import JWKSCache

# Pin RS256: Keycloak signs access tokens RS256; pinning rejects alg=none + HS256 confusion.
_ALLOWED_ALGORITHMS = ["RS256"]

# acr values that denote MFA was performed (matches the realm acr.loa.map "mfa" level).
_MFA_ACR_VALUES = {"mfa"}
# amr factors that denote a second factor was used.
_MFA_AMR_FACTORS = {"otp", "mfa", "hwk", "sms"}


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, derived from a verified access token."""

    subject: str
    roles: list[str]
    tenant_claims: dict[str, str]
    acr: str | None = None
    amr: list[str] = field(default_factory=list)

    def has_role(self, role: str) -> bool:
        return role in self.roles


def _assert_mfa(claims: dict) -> None:
    acr = claims.get("acr")
    amr = claims.get("amr") or []
    if isinstance(amr, str):
        amr = [amr]
    if acr in _MFA_ACR_VALUES:
        return
    if any(factor in _MFA_AMR_FACTORS for factor in amr):
        return
    raise AuthError("MFA claim absent (acr/amr): token did not complete MFA")


def _extract_roles(claims: dict) -> list[str]:
    realm_access = claims.get("realm_access") or {}
    roles = realm_access.get("roles") if isinstance(realm_access, dict) else None
    return list(roles) if roles else []


def _extract_tenant_claims(claims: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("site", "study"):
        value = claims.get(key)
        if value is not None:
            out[key] = str(value)
    return out


def verify_token(
    token: str,
    *,
    jwks: JWKSCache,
    issuer: str,
    audience: str,
) -> Principal:
    """Verify a Keycloak access token and return the :class:`Principal`.

    Raises :class:`AuthError` (401) on any failure: bad signature, ``alg=none``/HS256,
    wrong ``iss``/``aud``, expired, unresolvable ``kid``, or missing MFA.
    """
    # 1. Resolve the signing key by kid (unsigned/alg=none has no usable kid path either).
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"malformed token header: {exc}") from exc

    # Reject up-front if the header advertises a non-RS256 alg (alg=none / HS256).
    if header.get("alg") not in _ALLOWED_ALGORITHMS:
        raise AuthError(f"disallowed alg={header.get('alg')!r}; RS256 required")

    kid = header.get("kid")
    if not kid:
        raise AuthError("token header missing kid")
    public_key = jwks.get_key(kid)  # raises AuthError on unknown kid

    # 2-3. Decode with RS256 pinned + iss/aud/exp verification.
    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms=_ALLOWED_ALGORITHMS,
            audience=audience,
            issuer=issuer,
            options={
                "require": ["exp", "iss", "aud", "sub"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"token verification failed: {exc}") from exc

    # 4. Enforce MFA in the API tier (defence-in-depth; T-04-02).
    _assert_mfa(claims)

    return Principal(
        subject=str(claims["sub"]),
        roles=_extract_roles(claims),
        tenant_claims=_extract_tenant_claims(claims),
        acr=claims.get("acr"),
        amr=list(claims.get("amr") or []),
    )


def authn_dependency(*, jwks: JWKSCache, issuer: str, audience: str):
    """Build a FastAPI-style dependency that verifies the bearer token -> Principal.

    Framework-agnostic: returns a callable taking the raw ``Authorization`` header value
    (e.g. ``"Bearer eyJ..."``). The reference service (plan 01-05) wires this behind
    FastAPI's ``Security``/``Depends`` with an ``HTTPBearer`` extractor.
    """

    def _dependency(authorization: str | None) -> Principal:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise AuthError("missing or malformed Authorization: Bearer header")
        token = authorization.split(" ", 1)[1].strip()
        return verify_token(token, jwks=jwks, issuer=issuer, audience=audience)

    return _dependency
