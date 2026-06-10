"""Fail-closed request-scoped tenancy context (D-03, RESEARCH Pattern 3; T-04-04).

Tenancy is carried in a ``contextvar`` so the data layer can scope every query by site/study.
The load-bearing invariant is **fail-closed**: ``current_tenant()`` RAISES when no tenant has
been resolved for the request — a query may never run unscoped (cross-tenant leak / unscoped
read). These tests also prove contextvar isolation so two concurrent requests cannot leak
each other's tenant.
"""

from __future__ import annotations

import asyncio

import pytest

from veridoc_tenancy import (
    Tenant,
    TenancyError,
    current_tenant,
    set_tenant,
    tenant_from_claims,
    tenant_scope,
)


def test_current_tenant_unset_raises_fail_closed():
    # No tenant resolved for this context => must raise, never return a default.
    with pytest.raises(TenancyError):
        current_tenant()


def test_set_then_current_returns_tenant():
    token = set_tenant(Tenant(site="site-001", study="study-A"))
    try:
        t = current_tenant()
        assert t.site == "site-001"
        assert t.study == "study-A"
    finally:
        # Restore so this test does not leak into others.
        import veridoc_tenancy

        veridoc_tenancy.context._tenant_var.reset(token)


def test_tenant_scope_sets_and_clears():
    with tenant_scope(Tenant(site="site-XYZ", study="study-Z")):
        assert current_tenant().site == "site-XYZ"
    # After the scope exits, the context is cleared -> fail-closed again.
    with pytest.raises(TenancyError):
        current_tenant()


def test_tenant_from_claims_extracts_site_study():
    claims = {"site": "site-007", "study": "study-Q"}
    t = tenant_from_claims(claims)
    assert t == Tenant(site="site-007", study="study-Q")


def test_tenant_from_claims_missing_is_fail_closed():
    # A principal with no site/study claim cannot resolve a tenant -> raise (never default).
    with pytest.raises(TenancyError):
        tenant_from_claims({"site": "site-007"})  # missing study
    with pytest.raises(TenancyError):
        tenant_from_claims({})


def test_no_cross_request_leak_between_concurrent_contexts():
    """Two concurrent async tasks with different tenants must not see each other's context."""

    async def worker(site: str, study: str, hold: float) -> str:
        with tenant_scope(Tenant(site=site, study=study)):
            # Yield control so the other task interleaves while we hold our tenant.
            await asyncio.sleep(hold)
            return current_tenant().site

    async def run():
        # Task A sleeps longer; if contextvars leaked, A would observe B's site.
        results = await asyncio.gather(
            worker("site-A", "study-A", 0.02),
            worker("site-B", "study-B", 0.0),
        )
        return results

    results = asyncio.run(run())
    assert results == ["site-A", "site-B"]


def test_outer_context_still_fail_closed_after_concurrency():
    # The event loop tasks above must not have set the *outer* context.
    with pytest.raises(TenancyError):
        current_tenant()
