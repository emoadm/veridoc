"""Subject create/update — the ONE place all five shared libs meet (D-07).

A request reaching these handlers has already passed authn (JWKS RS256 + MFA, veridoc-auth)
and RBAC (``require_role``, deny-by-default) via FastAPI dependencies, and tenancy has been
resolved fail-closed (``current_tenant()``, veridoc-tenancy). Each handler then:

  1. derives the deterministic pseudonym token (veridoc-pseudonym),
  2. envelope-encrypts the PII field (veridoc-crypto) — only ciphertext lands at rest,
  3. INSERTs/UPDATEs the Subject row carrying ``tenant_id`` from ``current_tenant()``,
  4. calls ``append_audit`` on the SAME SQLAlchemy session (veridoc-audit) — no commit,
  5. commits ONCE, so the business row and its hash-chained audit row are atomic (D-05).

The audit ``before``/``after`` carry already-pseudonymized/encrypted references (the patient
token + a ciphertext digest), never plaintext PII (the audit SDK is value-agnostic, T-02-06).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from veridoc_audit import AuditEvent, append_audit
from veridoc_auth import Principal, check_roles
from veridoc_crypto import encrypt_field
from veridoc_pseudonym import pseudonym_token
from veridoc_tenancy import current_tenant

# Roles permitted to register/update a Subject (a permitted subset of the 8 realm roles).
# Deny-by-default: any other role (e.g. regulatory-affairs) gets 403 (T-05-03).
_WRITE_ROLES = ("site-coordinator", "data-manager", "principal-investigator")

router = APIRouter(prefix="/subjects", tags=["subjects"])


def require_write_role(request: Request) -> Principal:
    """Resolve the request Principal (bound by the app's authn dependency) and enforce RBAC.

    The authn+tenancy dependency mounted on the router stores the verified Principal on
    ``request.state.principal``; this deny-by-default check (veridoc-auth ``check_roles``)
    raises ``ForbiddenError`` (403) unless the caller holds a permitted write role.
    """
    principal: Principal | None = getattr(request.state, "principal", None)
    if principal is None:  # pragma: no cover - the authn dependency always sets it first
        from veridoc_auth import AuthError

        raise AuthError("no authenticated principal on request")
    check_roles(principal, _WRITE_ROLES)
    return principal


class SubjectCreate(BaseModel):
    """POST /subjects body (Pydantic v2; rejects unexpected fields — T-05-06)."""

    model_config = ConfigDict(extra="forbid")

    natural_id: str = Field(min_length=1, max_length=256)
    pii: str = Field(min_length=1, max_length=4096)


class SubjectUpdate(BaseModel):
    """PUT /subjects/{id} body."""

    model_config = ConfigDict(extra="forbid")

    pii: str = Field(min_length=1, max_length=4096)


class SubjectOut(BaseModel):
    """Response shape — NEVER echoes plaintext PII."""

    id: int
    tenant_id: str
    pseudonym_token: str


def _ct_digest(ciphertext: bytes) -> str:
    """A non-reversible digest of the ciphertext for the audit before/after payload."""
    return hashlib.sha256(ciphertext).hexdigest()


def get_session(request: Request) -> Session:
    """Request-scoped session dependency (one session per request)."""
    factory = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()


@router.post("", response_model=SubjectOut, status_code=201)
@router.post("/", response_model=SubjectOut, status_code=201, include_in_schema=False)
def create_subject(
    body: SubjectCreate,
    principal: Principal = Depends(require_write_role),
    session: Session = Depends(get_session),
) -> SubjectOut:
    tenant = current_tenant()  # fail-closed: raises TenancyError -> 401 if unresolved
    tenant_id = f"{tenant.site}/{tenant.study}"

    # The deterministic per-patient pseudonym token (veridoc-pseudonym) doubles as the
    # crypto patient_id at rest, so erasure (crypto-shred of this token) renders BOTH the
    # ciphertext undecryptable AND the token irrecomputable — without storing the natural_id.
    token = pseudonym_token(body.natural_id, body.natural_id)
    ciphertext = encrypt_field(token, body.pii)

    result = session.execute(
        text(
            "INSERT INTO subject (tenant_id, pseudonym_token, pii_ciphertext) "
            "VALUES (:t, :p, :c) RETURNING id"
        ),
        {"t": tenant_id, "p": token, "c": ciphertext},
    )
    subject_id = result.scalar_one()

    # Same-transaction hash-chained audit (D-05): NO commit inside append_audit.
    append_audit(
        session,
        AuditEvent(
            actor_id=principal.subject,
            actor_role=_primary_role(principal),
            tenant_id=tenant_id,
            action="create",
            entity_type="subject",
            entity_id=str(subject_id),
            before=None,
            after={"pseudonym_token": token, "pii_ciphertext_sha256": _ct_digest(ciphertext)},
            occurred_at=datetime.now(UTC),
        ),
    )
    session.commit()  # ONE commit: business row + audit row are atomic.

    return SubjectOut(id=subject_id, tenant_id=tenant_id, pseudonym_token=token)


@router.put("/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: int,
    body: SubjectUpdate,
    principal: Principal = Depends(require_write_role),
    session: Session = Depends(get_session),
) -> SubjectOut:
    tenant = current_tenant()
    tenant_id = f"{tenant.site}/{tenant.study}"

    existing = session.execute(
        text("SELECT tenant_id, pseudonym_token, pii_ciphertext FROM subject WHERE id = :i"),
        {"i": subject_id},
    ).one_or_none()
    if existing is None:
        raise HTTPException(status_code=404, detail="subject not found")
    # Cross-tenant access is denied (T-05-03): a subject in another tenant is invisible.
    if existing.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="cross-tenant access denied")

    token = existing.pseudonym_token
    # The pseudonym token is the stable per-patient id; re-encrypt the updated PII under it.
    new_ciphertext = encrypt_field(token, body.pii)
    before = {"pii_ciphertext_sha256": _ct_digest(bytes(existing.pii_ciphertext))}
    after = {"pii_ciphertext_sha256": _ct_digest(new_ciphertext)}

    session.execute(
        text("UPDATE subject SET pii_ciphertext = :c, updated_at = now() WHERE id = :i"),
        {"c": new_ciphertext, "i": subject_id},
    )

    append_audit(
        session,
        AuditEvent(
            actor_id=principal.subject,
            actor_role=_primary_role(principal),
            tenant_id=tenant_id,
            action="update",
            entity_type="subject",
            entity_id=str(subject_id),
            before=before,
            after=after,
            occurred_at=datetime.now(UTC),
        ),
    )
    session.commit()

    return SubjectOut(id=subject_id, tenant_id=tenant_id, pseudonym_token=token)


def _primary_role(principal: Principal) -> str:
    """The single role recorded on the audit row (the first permitted write role held)."""
    for role in _WRITE_ROLES:
        if principal.has_role(role):
            return role
    return principal.roles[0] if principal.roles else "unknown"
