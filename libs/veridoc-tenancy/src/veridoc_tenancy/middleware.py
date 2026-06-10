"""Request-scoped tenancy middleware (D-03, RESEARCH Pattern 3).

Resolves the request's :class:`Tenant` from the authenticated principal's site/study claims
(produced by ``veridoc-auth``'s ``Principal.tenant_claims``) and binds it into the
tenancy ``contextvar`` for the request lifespan, clearing it afterward. It is **fail-closed**:
if the principal carries no resolvable site/study, :func:`tenant_from_claims` raises and the
request is rejected before any unscoped query can run (T-04-04).

Two integration shapes are provided so the reference service (plan 01-05) can wire whichever
fits — a Starlette/ASGI ``BaseHTTPMiddleware`` subclass or a plain context manager. To avoid a
hard runtime coupling, the principal is consumed via duck typing on ``.tenant_claims``
(``veridoc-auth`` is an optional dependency; the contract is just a mapping of claims).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Protocol, runtime_checkable

from .context import Tenant, tenant_from_claims, tenant_scope


@runtime_checkable
class HasTenantClaims(Protocol):
    """Anything exposing ``tenant_claims`` (e.g. ``veridoc_auth.Principal``)."""

    tenant_claims: Mapping[str, object]


def resolve_tenant(principal: HasTenantClaims | Mapping[str, object]) -> Tenant:
    """Resolve a :class:`Tenant` from a principal (or a raw claims mapping), fail-closed."""
    claims: Mapping[str, object]
    if isinstance(principal, Mapping):
        claims = principal
    else:
        claims = getattr(principal, "tenant_claims", None) or {}
    return tenant_from_claims(claims)


@contextmanager
def tenancy_middleware(
    principal: HasTenantClaims | Mapping[str, object],
) -> Iterator[Tenant]:
    """Bind the principal's tenant for a request, clearing it on exit (fail-closed).

    Usage (per-request)::

        with tenancy_middleware(principal):
            handle_request()  # current_tenant() is available + scoped here
        # outside the block, current_tenant() is fail-closed again
    """
    tenant = resolve_tenant(principal)
    with tenant_scope(tenant) as bound:
        yield bound


def build_asgi_tenancy_middleware(principal_getter):
    """Build a Starlette ``BaseHTTPMiddleware`` that scopes tenancy per request.

    ``principal_getter(request)`` returns the authenticated principal (or claims mapping)
    for the request — the reference service supplies it from its auth dependency. Imported
    lazily so ``veridoc-tenancy`` carries no hard Starlette dependency.
    """
    from starlette.middleware.base import BaseHTTPMiddleware  # lazy: optional dep

    class TenancyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            principal = principal_getter(request)
            # fail-closed: tenant_from_claims raises if site/study are unresolvable.
            with tenancy_middleware(principal):
                return await call_next(request)

    return TenancyMiddleware
