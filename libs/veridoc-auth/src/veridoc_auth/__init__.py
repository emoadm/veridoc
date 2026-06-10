"""veridoc_auth — OIDC authn + 8-role RBAC + IP-allowlist middleware (D-01/D-02).

Verifies Keycloak-issued access tokens against the realm JWKS (RS256 signature +
iss/aud/exp), enforces MFA via the acr/amr claim, exposes deny-by-default 8-role RBAC, and
a data-driven per-tenant IP-allowlist hook. The API tier never handles credentials —
Keycloak owns auth/MFA/sessions (D-01); this only validates the JWT.

Public API (consumed by the reference service, plan 01-05):
    verify_token(token, *, jwks, issuer, audience) -> Principal
    authn_dependency(*, jwks, issuer, audience)     -> dependency(authorization) -> Principal
    require_role(*roles)                            -> dependency(Principal) -> Principal
    check_roles(principal, allowed)                 -> None (raises ForbiddenError)
    ip_allowlist_check(client_ip, *, tenant, allowlists) -> None (raises AuthError)
    Principal, JWKSCache, AuthError, ForbiddenError, EIGHT_ROLES
"""

from .allowlist import AllowlistMap, ip_allowlist_check
from .errors import AuthError, ForbiddenError
from .jwks import JWKSCache
from .middleware import Principal, authn_dependency, verify_token
from .rbac import EIGHT_ROLES, check_roles, require_role

__all__ = [
    "AllowlistMap",
    "AuthError",
    "EIGHT_ROLES",
    "ForbiddenError",
    "JWKSCache",
    "Principal",
    "authn_dependency",
    "check_roles",
    "ip_allowlist_check",
    "require_role",
    "verify_token",
]
