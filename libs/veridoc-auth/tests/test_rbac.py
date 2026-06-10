"""Deny-by-default 8-role RBAC and the data-driven IP-allowlist hook — T-04-03 / T-04-07."""

from __future__ import annotations

import pytest
from veridoc_auth import (
    AuthError,
    ForbiddenError,
    Principal,
    check_roles,
    ip_allowlist_check,
)


def _principal(roles):
    return Principal(
        subject="u1",
        roles=list(roles),
        tenant_claims={"site": "site-001", "study": "study-A"},
        acr="mfa",
        amr=["pwd", "otp"],
    )


def test_permitted_role_passes():
    p = _principal(["medical-monitor"])
    # Should not raise.
    check_roles(p, ("medical-monitor",))


def test_cross_role_request_is_forbidden():
    p = _principal(["cra"])
    with pytest.raises(ForbiddenError):
        check_roles(p, ("medical-monitor",))


def test_any_of_multiple_allowed_roles_passes():
    p = _principal(["regulatory-affairs"])
    check_roles(p, ("medical-monitor", "regulatory-affairs"))


def test_no_roles_is_denied_by_default():
    p = _principal([])
    with pytest.raises(ForbiddenError):
        check_roles(p, ("cra",))


def test_require_role_dependency_factory_returns_callable():
    from veridoc_auth import require_role

    dep = require_role("system-admin")
    assert callable(dep)
    admin = _principal(["system-admin"])
    assert dep(admin) is admin
    with pytest.raises(ForbiddenError):
        dep(_principal(["cra"]))


# --- IP allowlist (data-driven, per-tenant) -----------------------------------


def test_allowlist_allows_when_unset():
    # No allowlist configured for the tenant => allow (hook is opt-in / data-driven).
    ip_allowlist_check("203.0.113.7", tenant="site-001", allowlists={})


def test_allowlist_denies_unlisted_ip():
    allowlists = {"site-001": ["198.51.100.0/24"]}
    with pytest.raises(AuthError):
        ip_allowlist_check("203.0.113.7", tenant="site-001", allowlists=allowlists)


def test_allowlist_allows_listed_ip():
    allowlists = {"site-001": ["198.51.100.0/24", "203.0.113.7/32"]}
    ip_allowlist_check("203.0.113.7", tenant="site-001", allowlists=allowlists)


def test_allowlist_is_per_tenant():
    # An allowlist on a DIFFERENT tenant does not constrain this tenant.
    allowlists = {"site-999": ["198.51.100.0/24"]}
    ip_allowlist_check("203.0.113.7", tenant="site-001", allowlists=allowlists)
