"""Auth error types.

``AuthError`` -> 401 (authentication failed: bad/expired/forged token, missing MFA,
unresolvable signer, IP not allowed). ``ForbiddenError`` -> 403 (authenticated but the
principal's role is not permitted — deny-by-default RBAC).

These are plain exceptions so the libs stay framework-agnostic; the reference service
(plan 01-05) maps them to FastAPI ``HTTPException`` 401/403 at the boundary.
"""

from __future__ import annotations


class AuthError(Exception):
    """Authentication failed — maps to HTTP 401."""

    status_code = 401


class ForbiddenError(Exception):
    """Authenticated but not authorized — maps to HTTP 403 (deny-by-default RBAC)."""

    status_code = 403
