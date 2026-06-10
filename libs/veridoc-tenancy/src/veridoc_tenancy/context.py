"""Request-scoped tenancy context (D-03, RESEARCH Pattern 3).

The current request's :class:`Tenant` (site + study) lives in a ``contextvar`` so the data
layer can scope every query and stamp every audit row without threading the tenant through
every call. The invariant is **fail-closed**: :func:`current_tenant` RAISES :class:`TenancyError`
when no tenant has been resolved — a query may never run unscoped (cross-tenant leak,
T-04-04). There is no default tenant.

``contextvars`` gives per-task / per-request isolation: each asyncio task (and each thread,
via copies) sees its own value, so concurrent requests with different tenants never leak
into one another.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass


class TenancyError(RuntimeError):
    """Raised when the tenancy context is missing or cannot be resolved (fail-closed)."""


@dataclass(frozen=True)
class Tenant:
    """The request-scoped tenancy identity: a (site, study) pair."""

    site: str
    study: str


# The single source of request-scoped tenancy. No default => unset reads fail closed.
_tenant_var: ContextVar[Tenant] = ContextVar("veridoc_tenant")


def current_tenant() -> Tenant:
    """Return the request's :class:`Tenant`, or raise :class:`TenancyError` (fail-closed).

    Never returns a default/unscoped value — callers in the data layer rely on this to
    guarantee every query is tenant-scoped.
    """
    try:
        return _tenant_var.get()
    except LookupError as exc:
        raise TenancyError(
            "no tenant resolved for this request (fail-closed): refusing to run unscoped"
        ) from exc


def set_tenant(tenant: Tenant) -> Token:
    """Set the request tenant, returning a token usable to reset the context."""
    return _tenant_var.set(tenant)


def reset_tenant(token: Token) -> None:
    """Reset the tenancy context to its prior state (clears the request tenant)."""
    _tenant_var.reset(token)


@contextmanager
def tenant_scope(tenant: Tenant) -> Iterator[Tenant]:
    """Bind ``tenant`` for the duration of the ``with`` block, clearing it afterward.

    After the block exits, :func:`current_tenant` is fail-closed again.
    """
    token = _tenant_var.set(tenant)
    try:
        yield tenant
    finally:
        _tenant_var.reset(token)


def tenant_from_claims(claims: Mapping[str, object]) -> Tenant:
    """Build a :class:`Tenant` from a principal's site/study claims (fail-closed).

    Raises :class:`TenancyError` when either claim is absent — a principal that cannot
    resolve a tenant must NOT default to an unscoped or partial tenant (D-03).
    """
    site = claims.get("site")
    study = claims.get("study")
    if not site or not study:
        raise TenancyError(
            "principal claims lack a resolvable site/study tenant "
            f"(site={site!r}, study={study!r}) — fail-closed"
        )
    return Tenant(site=str(site), study=str(study))
