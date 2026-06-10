"""Login-attempt auditing (21 CFR Part 11 / Annex 11 access logging).

Every authentication attempt at the service edge — success AND failure — must leave an
immutable audit record. The reference service audits this once, in the authn dependency, so
Phases 2-7 inherit the behaviour:

* on a verified token -> ``login-success`` (actor = the token subject, tenant from claims);
* on a rejected token (bad signature, missing MFA, etc.) -> ``login-failure`` (actor is the
  best-effort unverified subject, or "unknown" when the token is unparseable).

Each login audit row is written in its own short transaction (the login event is not part of
a business write) and committed, so the attempt is recorded even when the request is rejected.
The append-only audit chain still verifies afterward (the rows are appended, never mutated).
"""

from __future__ import annotations

from datetime import UTC, datetime

import jwt
from sqlalchemy.orm import sessionmaker
from veridoc_audit import AuditEvent, append_audit


def _unverified_subject(token: str) -> str:
    """Best-effort actor id for a FAILED login (claims are NOT trusted, only logged)."""
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        return str(claims.get("sub") or "unknown")
    except Exception:
        return "unknown"


def _unverified_tenant(token: str) -> str:
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
        site = claims.get("site")
        study = claims.get("study")
        if site and study:
            return f"{site}/{study}"
    except Exception:
        pass
    return "unknown"


def audit_login_success(factory: sessionmaker, *, subject: str, tenant_id: str, role: str) -> None:
    """Append a ``login-success`` audit row in its own committed transaction."""
    _append_login(factory, action="login-success", actor_id=subject, role=role, tenant_id=tenant_id)


def audit_login_failure(factory: sessionmaker, *, token: str, reason: str) -> None:
    """Append a ``login-failure`` audit row for a rejected attempt (best-effort actor)."""
    _append_login(
        factory,
        action="login-failure",
        actor_id=_unverified_subject(token),
        role="unknown",
        tenant_id=_unverified_tenant(token),
        reason=reason,
    )


def _append_login(
    factory: sessionmaker,
    *,
    action: str,
    actor_id: str,
    role: str,
    tenant_id: str,
    reason: str | None = None,
) -> None:
    session = factory()
    try:
        append_audit(
            session,
            AuditEvent(
                actor_id=actor_id,
                actor_role=role,
                tenant_id=tenant_id,
                action=action,
                entity_type="auth",
                entity_id=actor_id,
                before=None,
                after={"reason": reason} if reason else None,
                occurred_at=datetime.now(UTC),
            ),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
