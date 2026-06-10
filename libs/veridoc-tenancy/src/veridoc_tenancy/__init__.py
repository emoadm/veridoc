"""veridoc_tenancy — fail-closed request-scoped site/study tenancy context (D-03).

Carries the request's (site, study) tenant in a ``contextvar`` so the data layer scopes
every query and stamps every audit row. Fail-closed: ``current_tenant()`` raises
``TenancyError`` when no tenant is resolved — a query may never run unscoped (T-04-04).
The tenant is sourced from the authenticated principal's claims (``veridoc-auth``'s
``Principal.tenant_claims``) by the tenancy middleware.

Public API (consumed by the reference service, plan 01-05):
    current_tenant() -> Tenant                       # raises TenancyError if unset
    set_tenant(tenant) -> Token / reset_tenant(token)
    tenant_scope(tenant)                             # context manager (set + clear)
    tenant_from_claims(claims) -> Tenant             # fail-closed claim extraction
    tenancy_middleware(principal)                    # per-request scope from a principal
    build_asgi_tenancy_middleware(principal_getter)  # Starlette middleware factory
    Tenant, TenancyError
"""

from . import context
from .context import (
    TenancyError,
    Tenant,
    current_tenant,
    reset_tenant,
    set_tenant,
    tenant_from_claims,
    tenant_scope,
)
from .middleware import (
    build_asgi_tenancy_middleware,
    resolve_tenant,
    tenancy_middleware,
)

__all__ = [
    "Tenant",
    "TenancyError",
    "build_asgi_tenancy_middleware",
    "context",
    "current_tenant",
    "resolve_tenant",
    "reset_tenant",
    "set_tenant",
    "tenancy_middleware",
    "tenant_from_claims",
    "tenant_scope",
]
