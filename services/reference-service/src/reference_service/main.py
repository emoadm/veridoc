"""FastAPI reference service — the D-07 walking skeleton.

Composes the five shared platform libs into one HTTP service:

    HTTP request
      -> authn dependency (veridoc-auth: JWKS RS256 verify + iss/aud/exp + MFA acr/amr)
      -> tenancy bind (veridoc-tenancy: fail-closed site/study from the Principal claims)
      -> RBAC (veridoc-auth require_role, deny-by-default) on the route
      -> Subject handler (veridoc-pseudonym + veridoc-crypto + same-transaction veridoc-audit)
      -> Postgres (business row + hash-chained audit row commit atomically)

``/healthz`` is the only unauthenticated route (k8s liveness). All lib exceptions are mapped
to HTTP status codes at the boundary (AuthError->401, ForbiddenError->403, TenancyError->401).
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from veridoc_auth import AuthError, ForbiddenError, JWKSCache, Principal, verify_token
from veridoc_tenancy import TenancyError, reset_tenant, set_tenant, tenant_from_claims

from .api import subjects
from .api.auth_audit import audit_login_failure, audit_login_success
from .config import Settings, get_settings
from .db import make_engine, make_session_factory


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("missing or malformed Authorization: Bearer header")
    return authorization.split(" ", 1)[1].strip()


def _make_principal_dependency(
    *, jwks: JWKSCache, issuer: str, audience: str
) -> Callable[[Request], Principal]:
    """Build the authn + fail-closed tenancy dependency.

    Verifies the bearer token to a :class:`Principal`, then binds the request tenant from the
    Principal's site/study claims (fail-closed) for the duration of the request, clearing it
    afterward. RBAC (``require_role``) runs after this on the route.
    """

    async def _principal(request: Request) -> Principal:
        # Async generator dependency: setup + teardown run in the SAME asyncio context, so
        # the tenancy contextvar token stays valid (a sync dependency would set/reset across
        # different threadpool contexts and raise on reset).
        factory = request.app.state.session_factory
        try:
            token = _bearer_token(request)
        except AuthError as exc:
            # No bearer header at all — record the failed attempt and reject.
            audit_login_failure(factory, token="", reason=str(exc))
            raise
        try:
            principal = verify_token(token, jwks=jwks, issuer=issuer, audience=audience)
            # Fail-closed tenancy: raises TenancyError if site/study are unresolvable.
            tenant = tenant_from_claims(principal.tenant_claims)
        except (AuthError, TenancyError) as exc:
            # Every REJECTED login attempt is audited (success+failure both logged, T-05-05).
            audit_login_failure(factory, token=token, reason=str(exc))
            raise
        # Every SUCCESSFUL authentication is audited before the business handler runs.
        audit_login_success(
            factory,
            subject=principal.subject,
            tenant_id=f"{tenant.site}/{tenant.study}",
            role=principal.roles[0] if principal.roles else "unknown",
        )
        token_obj = set_tenant(tenant)
        # Expose the verified principal to the route's RBAC dependency.
        request.state.principal = principal
        try:
            yield principal
        finally:
            reset_tenant(token_obj)

    return _principal


def create_app(
    *,
    engine: Engine | None = None,
    jwks: JWKSCache | None = None,
    issuer: str | None = None,
    audience: str | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Build the FastAPI app. Injectable engine/jwks/issuer/audience for tests."""
    settings = settings or get_settings()
    issuer = issuer or settings.keycloak_issuer
    audience = audience or settings.keycloak_audience
    engine = engine or make_engine(settings.database_url)
    jwks = jwks or JWKSCache(jwks_uri=settings.keycloak_jwks_uri)

    app = FastAPI(title="VeriDoc Reference Service", version="0.1.0")
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.jwks = jwks

    # Map lib exceptions to HTTP status at the boundary (framework-agnostic libs).
    @app.exception_handler(AuthError)
    async def _auth_error(_request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(TenancyError)
    async def _tenancy_error(_request: Request, exc: TenancyError) -> JSONResponse:
        # No resolvable tenant => the caller is not properly authenticated/scoped (401).
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    principal_dependency = _make_principal_dependency(jwks=jwks, issuer=issuer, audience=audience)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Liveness probe — open (no auth), per k8s requirements."""
        return {"status": "ok"}

    # Mount the authn + fail-closed tenancy dependency on the whole subjects router. It runs
    # BEFORE each route's deny-by-default RBAC check (which reads request.state.principal).
    app.include_router(
        subjects.router,
        dependencies=[Depends(principal_dependency)],
    )

    return app


# Module-level app for ``uvicorn reference_service.main:app`` (production entrypoint).
app = create_app()
