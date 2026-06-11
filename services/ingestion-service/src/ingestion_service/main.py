"""FastAPI ingestion service — thin async ingest endpoint (D-04 / D-06).

Cloned from ``services/reference-service/main.py`` (exact analog in 02-PATTERNS.md)
and extended with:

- A ``lifespan`` hook that creates MongoDB indexes (Pitfall 6 guard) and initialises
  the RQ ingestion queue with JSONSerializer (Pitfall 3 guard / T-02-SVC-03).
- An ``/ingest/{site_id}`` router instead of ``/subjects``.

The auth/tenancy/RBAC machinery (``_bearer_token``, ``_make_principal_dependency``,
exception handlers, ``/healthz``) is copied verbatim from the reference service.

Security (inherited from Phase 1):
- RS256 + MFA enforced (T-02-SVC-01, veridoc-auth).
- Fail-closed tenancy (T-02-SVC-02, veridoc-tenancy).
- Deny-by-default RBAC on the ingest router (T-02-SVC-01).
- JSONSerializer eliminates pickle RCE from the RQ queue (T-02-SVC-03).
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from veridoc_auth import AuthError, ForbiddenError, JWKSCache, Principal, verify_token
from veridoc_tenancy import TenancyError, reset_tenant, set_tenant, tenant_from_claims

from .api import ingest as ingest_router_module
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
    """Build the authn + fail-closed tenancy dependency (verbatim from reference-service)."""

    async def _principal(request: Request) -> Principal:
        factory = request.app.state.session_factory
        try:
            token = _bearer_token(request)
        except AuthError as exc:
            audit_login_failure(factory, token="", reason=str(exc))
            raise
        try:
            principal = verify_token(token, jwks=jwks, issuer=issuer, audience=audience)
            tenant = tenant_from_claims(principal.tenant_claims)
        except (AuthError, TenancyError) as exc:
            audit_login_failure(factory, token=token, reason=str(exc))
            raise
        audit_login_success(
            factory,
            subject=principal.subject,
            tenant_id=f"{tenant.site}/{tenant.study}",
            role=principal.roles[0] if principal.roles else "unknown",
        )
        token_obj = set_tenant(tenant)
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
    """Build the FastAPI ingestion-service app.

    Injectable ``engine``/``jwks``/``issuer``/``audience`` for tests (mirrors
    reference-service ``create_app`` signature exactly). The lifespan hook
    initialises MongoDB indexes (Pitfall 6) and the RQ Queue with JSONSerializer
    (Pitfall 3 / T-02-SVC-03).
    """
    settings = settings or get_settings()
    issuer = issuer or settings.keycloak_issuer
    audience = audience or settings.keycloak_audience
    engine = engine or make_engine(settings.database_url)
    jwks = jwks or JWKSCache(jwks_uri=settings.keycloak_jwks_uri)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Startup: create MongoDB indexes + RQ Queue. Teardown: close Mongo client."""
        from redis import Redis
        from rq import Queue
        from rq.serializers import JSONSerializer
        from veridoc_fhir.repository import FhirRepository

        # MongoDB indexes — MUST be created at startup (Pitfall 6 guard).
        repo = FhirRepository(mongo_url=settings.mongodb_url)
        await repo.create_indexes()
        app.state.fhir_repo = repo

        # RQ ingestion queue with JSONSerializer (Pitfall 3 guard / T-02-SVC-03).
        app.state.rq_queue = Queue(
            "ingestion",
            connection=Redis.from_url(settings.redis_url),
            serializer=JSONSerializer,
        )

        # Blob store config stored on app.state for the ingest handler
        app.state.blob_endpoint_url = settings.blob_endpoint_url
        app.state.blob_bucket = settings.blob_bucket
        app.state.blob_access_key = settings.blob_access_key
        app.state.blob_secret_key = settings.blob_secret_key

        yield

        # Teardown: close the MongoDB client
        repo.close()

    app = FastAPI(
        title="VeriDoc Ingestion Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.jwks = jwks

    # Map lib exceptions to HTTP status codes at the boundary.
    @app.exception_handler(AuthError)
    async def _auth_error(_request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(TenancyError)
    async def _tenancy_error(_request: Request, exc: TenancyError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    principal_dependency = _make_principal_dependency(jwks=jwks, issuer=issuer, audience=audience)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Liveness probe — open (no auth)."""
        return {"status": "ok"}

    # Mount authn + fail-closed tenancy dependency on the whole ingest router.
    app.include_router(
        ingest_router_module.router,
        dependencies=[Depends(principal_dependency)],
    )

    return app


# Module-level app for ``uvicorn ingestion_service.main:app`` (production entrypoint).
app = create_app()
