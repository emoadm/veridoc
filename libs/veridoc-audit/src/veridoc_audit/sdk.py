"""Same-transaction, advisory-locked audit writer (D-05, Pitfall 1 / Pitfall 5).

:func:`append_audit` joins the CALLER's open transaction: it reads the chain head, computes
``record_hash``, inserts one append-only row, and returns the hash — but **never commits**.
The caller's transaction owns the commit, so a business write and its audit row are atomic
(forcing the audit insert to fail rolls back the business write — threat T-02-04 / Pitfall 5).

Chain-head access is serialized with a Postgres transaction-scoped advisory lock
(``pg_advisory_xact_lock``) so two concurrent writers cannot read the same ``prev_hash`` and
fork the chain (threat T-02-03 / Pitfall 1). The lock is released automatically at commit/rollback.
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ._payload import build_hash_payload
from .chain import compute_record_hash
from .chain import verify_chain as _verify_rows
from .models import AuditEvent, AuditLog

__all__ = ["append_audit", "verify_chain", "AUDIT_CHAIN_LOCK_KEY"]

# A fixed, process-wide key identifying the single audit-chain stream. All writers contend
# on this one advisory lock, serializing the chain-head read-modify-write.
AUDIT_CHAIN_LOCK_KEY = 0x5645_7249_4441_4C00  # "VerIDAL\0" — stable, arbitrary 64-bit int


def append_audit(session: Session, event: AuditEvent) -> str:
    """Append one audit row inside ``session``'s open transaction; return its ``record_hash``.

    Does NOT commit — the caller's transaction owns the commit (D-05). Serializes on the
    chain head via ``pg_advisory_xact_lock`` to prevent forks (Pitfall 1).
    """
    # 1. Serialize chain-head access for the remainder of this transaction (Pitfall 1).
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": AUDIT_CHAIN_LOCK_KEY})

    # 2. Read the current chain head; genesis prev_hash is "" (empty string).
    prev_hash = (
        session.execute(
            select(AuditLog.record_hash).order_by(AuditLog.id.desc()).limit(1)
        ).scalar_one_or_none()
        or ""
    )

    # 3. Compute record_hash over the deterministic JCS payload.
    payload = event.hash_payload()
    record_hash = compute_record_hash(prev_hash, payload)

    # 4. Insert the append-only row (parameterized — threat T-02-05). NO commit (Pitfall 5).
    row = AuditLog(
        prev_hash=prev_hash,
        record_hash=record_hash,
        actor_id=event.actor_id,
        actor_role=event.actor_role,
        tenant_id=event.tenant_id,
        action=event.action,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        before=event.before,
        after=event.after,
        agent_decision=event.agent_decision,
        agent_confidence=event.agent_confidence,
        occurred_at=event.occurred_at,
    )
    session.add(row)
    session.flush()  # emit the INSERT within the caller's txn (surfaces constraint errors now)

    return record_hash


def verify_chain(session: Session) -> bool:
    """Re-walk the persisted ``audit_log`` rows (id order); ``True`` iff the chain is intact.

    Reconstructs each row's hash payload from its persisted columns and delegates to the
    pure in-memory walk. A row whose payload no longer hashes to its stored ``record_hash``
    (tampering) or whose ``prev_hash`` link is broken (fork) yields ``False``.
    """
    rows = session.execute(select(AuditLog).order_by(AuditLog.id.asc())).scalars().all()
    walk_rows = [
        {
            "prev_hash": r.prev_hash,
            "record_hash": r.record_hash,
            "payload": _row_hash_payload(r),
        }
        for r in rows
    ]
    return _verify_rows(walk_rows)


def _row_hash_payload(row: AuditLog) -> dict:
    """Reconstruct the deterministic hash payload from a persisted row.

    Uses the same ``_payload`` helper as :meth:`AuditEvent.hash_payload`, so a row written
    by ``append_audit`` re-hashes to its stored ``record_hash`` (occurred_at normalized to
    UTC, agent_confidence Decimal->float).
    """
    return build_hash_payload(
        actor_id=row.actor_id,
        actor_role=row.actor_role,
        tenant_id=row.tenant_id,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        before=row.before,
        after=row.after,
        agent_decision=row.agent_decision,
        agent_confidence=row.agent_confidence,
        occurred_at=row.occurred_at,
    )
