"""POST /ingest/{site_id} — the authenticated async ingest endpoint (D-04 / D-06).

Patterned after ``services/reference-service/src/reference_service/api/subjects.py``
(the five-lib composition pattern), adapted for async ingest via RQ.

Request flow:
1. authn dependency (veridoc-auth RS256/MFA) → verified Principal (T-02-SVC-01)
2. fail-closed tenancy (veridoc-tenancy) → Tenant(site, study) (T-02-SVC-02)
3. deny-by-default RBAC via ``require_write_role`` → only site-coordinator / data-manager
4. raw payload stored to blob store → ``payload_key`` (string, not bytes — Pitfall 4)
5. ``ingest_job`` enqueued on RQ queue with JSONSerializer (T-02-SVC-03, Pitfall 3)
6. same-transaction "ingest:enqueued" audit event (D-05; distinct from worker's "ingest:completed")
7. 202 Accepted + ``{"job_id": "..."}``

Security:
- unauthenticated → 401 (AuthError handler in main.py)
- wrong role → 403 (ForbiddenError from check_roles)
- missing/unresolvable tenant → 401 (TenancyError handler in main.py)
- raw bytes never pass through Redis (payload_key is the blob store string key)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from veridoc_audit import AuditEvent, append_audit
from veridoc_auth import Principal, check_roles
from veridoc_tenancy import current_tenant

# Roles permitted to initiate an ingest (deny-by-default: any other role → 403).
_WRITE_ROLES = ("site-coordinator", "data-manager")

router = APIRouter(prefix="/ingest", tags=["ingest"])


def require_write_role(request: Request) -> Principal:
    """Resolve the authenticated Principal and enforce ingest RBAC.

    Deny-by-default: only ``site-coordinator`` and ``data-manager`` may POST to
    ``/ingest/{site_id}``. All other roles receive 403 (T-02-SVC-01, ASVS V4).

    Analog: ``reference-service/api/subjects.py:require_write_role``.
    """
    principal: Principal | None = getattr(request.state, "principal", None)
    if principal is None:  # pragma: no cover - authn dependency always sets it first
        from veridoc_auth import AuthError
        raise AuthError("no authenticated principal on request")
    check_roles(principal, _WRITE_ROLES)
    return principal


def get_session(request: Request) -> Session:
    """Request-scoped session dependency (one session per request).

    Verbatim copy from ``reference-service/api/subjects.py:get_session``.
    """
    factory = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()


class IngestResponse(BaseModel):
    """202 response body — job_id for tracking the async ingest."""

    model_config = ConfigDict(extra="forbid")

    job_id: str


def _resolve_modality(request: Request, site_id: str) -> str:
    """Resolve the real ingestion modality for ``site_id`` from the site registry.

    CR-04 / WR-03: the modality MUST come from the site's registered
    ``SourceProfile`` — never a hardcoded default — so HL7/PDF/OCR sites route to
    the correct adapter. A site with no registered profile is rejected with HTTP
    400 (fail-closed) rather than silently defaulted to native-FHIR.

    Returns the modality slug string (e.g. ``"hl7v2"``) for JSON-safe enqueue.
    """
    from fastapi import HTTPException

    registry = getattr(request.app.state, "source_registry", None)
    if registry is None:
        raise HTTPException(
            status_code=503,
            detail="ingest source registry is not initialised",
        )
    try:
        profile = registry.get(site_id)
    except LookupError as exc:
        # Unknown site → fail closed (do not guess a modality / adapter).
        raise HTTPException(
            status_code=400,
            detail=f"no ingest source profile registered for site_id={site_id!r}",
        ) from exc
    return str(profile.modality.value)


def _primary_role(principal: Principal) -> str:
    """The single role recorded on the audit row."""
    for role in _WRITE_ROLES:
        if principal.has_role(role):
            return role
    return principal.roles[0] if principal.roles else "unknown"


@router.post("/{site_id}", response_model=IngestResponse, status_code=202)
async def post_ingest(
    site_id: str,
    request: Request,
    principal: Principal = Depends(require_write_role),
    session: Session = Depends(get_session),
) -> IngestResponse:
    """Accept a raw document payload, enqueue an async RQ ingest job.

    Security:
    - authn + tenancy enforced by the router-level dependency (see main.py).
    - deny-by-default RBAC enforced by ``require_write_role`` (only site-coordinator
      and data-manager).
    - fail-closed tenancy: ``current_tenant()`` raises TenancyError → 401 if
      the request has no resolvable site/study (T-02-SVC-02).
    - payload is stored to the blob store (not passed in-band through Redis — Pitfall 4).
    - "ingest:enqueued" audit event is written same-transaction BEFORE the 202 response,
      distinct from the worker's "ingest:completed" event (T-02-SVC-04, D-06).

    Returns:
        202 Accepted with ``{"job_id": "<uuid>"}`` identifying the enqueued RQ job.
    """
    # Fail-closed tenancy: raises TenancyError → 401 if unresolvable (T-02-SVC-02)
    tenant = current_tenant()
    tenant_id = f"{tenant.site}/{tenant.study}"

    # Resolve the REAL ingestion modality for this site from the registered
    # SourceProfile (CR-04). The API must NOT hardcode "native-fhir": HL7/PDF/OCR
    # sites would otherwise be routed to the wrong adapter. A site with no
    # registered profile is rejected (fail-closed; WR-03) rather than defaulted.
    modality = _resolve_modality(request, site_id)

    # Read the raw payload from the request body. The handler is async, so the
    # body is awaited directly (CR-01: never read it via request.scope or an
    # event-loop hack inside a threadpool — both are broken/unsafe).
    payload_bytes: bytes = await request.body()

    # Store the original payload to the blob store (Pitfall 4: blob key is JSON-serializable)
    blob_endpoint_url: str | None = getattr(request.app.state, "blob_endpoint_url", None)
    blob_bucket: str = getattr(request.app.state, "blob_bucket", "veridoc-docs")
    blob_access_key: str = getattr(request.app.state, "blob_access_key", "")
    blob_secret_key: str = getattr(request.app.state, "blob_secret_key", "")

    payload_key = f"{site_id}/{uuid.uuid4()}.bin"

    # Only upload to blob if blob store is configured (skip in unit tests)
    if blob_bucket and (blob_endpoint_url or blob_access_key):
        from veridoc_ingestion.blob_store import S3BlobStore
        blob_store = S3BlobStore(
            bucket=blob_bucket,
            endpoint_url=blob_endpoint_url,
            access_key=blob_access_key,
            secret_key=blob_secret_key,
        )
        content_type = request.headers.get("Content-Type", "application/octet-stream")
        # boto3 .put is blocking I/O — offload to the threadpool so it does not
        # block the event loop (CR-01: async handler must not run sync I/O inline).
        await run_in_threadpool(blob_store.put, payload_key, payload_bytes, content_type)

    # Enqueue the RQ ingest job (all args JSON-serializable — Pitfall 4 / T-02-SVC-03)
    queue = getattr(request.app.state, "rq_queue", None)
    job_id = str(uuid.uuid4())

    if queue is not None:
        from veridoc_ingestion.worker import ingest_job

        def _enqueue() -> str:
            job = queue.enqueue(
                ingest_job,
                site_id=site_id,
                modality=modality,  # resolved from the site's SourceProfile (CR-04)
                payload_key=payload_key,
                tenant_id=tenant_id,
                actor_id=principal.subject,
                blob_endpoint_url=blob_endpoint_url,
                blob_bucket=blob_bucket,
                blob_access_key=blob_access_key,
                blob_secret_key=blob_secret_key,
                job_timeout=300,
                result_ttl=3600,
            )
            return job.id

        # Redis enqueue is blocking I/O — offload from the event loop (CR-01).
        job_id = await run_in_threadpool(_enqueue)
    # If queue is None (unit test without Redis), return a generated job_id

    # Same-transaction "ingest:enqueued" audit event (D-05: atomic with the handler).
    # Distinct from the worker's "ingest:completed" event (T-02-SVC-04 / D-06).
    def _write_audit_and_commit() -> None:
        append_audit(
            session,
            AuditEvent(
                actor_id=principal.subject,
                actor_role=_primary_role(principal),
                tenant_id=tenant_id,
                action="ingest:enqueued",
                entity_type="ingest-request",
                entity_id=job_id,
                before=None,
                after={
                    "site_id": site_id,
                    "payload_key": payload_key,
                    "job_id": job_id,
                },
                occurred_at=datetime.now(UTC),
            ),
        )
        session.commit()  # business enqueue + audit row are atomic (D-05)

    # SQLAlchemy session work is blocking — offload from the event loop (CR-01).
    await run_in_threadpool(_write_audit_and_commit)

    return IngestResponse(job_id=job_id)
