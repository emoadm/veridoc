"""Deny-by-default 8-role RBAC (RESEARCH Pattern 2; T-04-03).

The 8 realm roles (kebab-case) are defined in ``deploy/keycloak/veridoc-realm.json`` and
their permissions in ``docs/validation/RBAC-MATRIX.md``. Enforcement here is **deny-by-
default**: a request passes only if the principal holds at least one of the explicitly
required roles; otherwise :class:`ForbiddenError` (403). There is no implicit inheritance.
"""

from __future__ import annotations

from collections.abc import Iterable

from .errors import ForbiddenError
from .middleware import Principal

# The canonical 8 realm roles (must match the committed realm export + RBAC matrix).
EIGHT_ROLES: frozenset[str] = frozenset(
    {
        "cra",
        "data-manager",
        "medical-monitor",
        "site-coordinator",
        "principal-investigator",
        "sponsor-rep",
        "regulatory-affairs",
        "system-admin",
    }
)


def check_roles(principal: Principal, allowed: Iterable[str]) -> None:
    """Raise :class:`ForbiddenError` unless the principal holds one of ``allowed`` roles.

    Deny-by-default: an empty ``allowed`` set, or a principal with no matching role, is
    forbidden.
    """
    allowed_set = set(allowed)
    if not allowed_set & set(principal.roles):
        raise ForbiddenError(
            f"principal {principal.subject!r} (roles={sorted(principal.roles)}) "
            f"lacks any required role {sorted(allowed_set)}"
        )


def require_role(*roles: str):
    """Build a deny-by-default RBAC dependency for the given role(s).

    Returns a callable that takes the authenticated :class:`Principal` and returns it
    unchanged when permitted, else raises :class:`ForbiddenError` (403). The reference
    service (plan 01-05) composes this after ``authn_dependency`` via FastAPI ``Depends``.
    """
    if not roles:
        raise ValueError("require_role needs at least one role (deny-by-default)")
    unknown = set(roles) - EIGHT_ROLES
    if unknown:
        raise ValueError(f"unknown realm role(s): {sorted(unknown)}")

    def _dependency(principal: Principal) -> Principal:
        check_roles(principal, roles)
        return principal

    return _dependency
