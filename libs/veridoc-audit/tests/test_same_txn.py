"""Same-transaction atomicity (D-05, threat T-02-04 / Pitfall 5).

append_audit joins the caller's transaction and never commits internally. If the audit
INSERT fails inside the caller's transaction, the *business* write in that same transaction
must roll back — there is never a business change without its audit row.

We model a business write with a durable table, then force the audit insert to fail (a
record_hash UNIQUE collision) inside the same transaction and assert zero business rows
persist. Also asserts append_audit does NOT commit on its own.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from veridoc_audit import AuditEvent, append_audit, compute_record_hash


def _event(n: int) -> AuditEvent:
    return AuditEvent(
        actor_id="user-1",
        actor_role="DataManager",
        tenant_id="study-A/site-1",
        action="update",
        entity_type="subject",
        entity_id=f"subj-{n}",
        before={"v": n - 1},
        after={"v": n},
        occurred_at=datetime(2026, 6, 11, 9, 30, n, tzinfo=UTC),
    )


def test_append_audit_does_not_commit(session):
    """After append_audit + rollback (no caller commit), nothing persists."""
    append_audit(session, _event(1))
    session.rollback()
    count = session.execute(text("SELECT count(*) FROM audit_log")).scalar_one()
    assert count == 0


def test_audit_failure_rolls_back_business_write(session):
    """Force the audit INSERT to fail -> the business write in the SAME txn rolls back.

    A real durable business table is created and committed up front. Inside one open
    transaction we (1) write a business row, then (2) drive append_audit into a failure by
    pre-seeding a record_hash collision (UNIQUE on record_hash). Because both writes share
    the caller's transaction, rolling back after the failure must leave ZERO business rows.
    """
    # Durable business table, committed so it survives the rollback under test.
    session.execute(text("CREATE TABLE IF NOT EXISTS business_write (id int PRIMARY KEY)"))
    session.commit()

    try:
        ev = _event(1)
        # Pick an arbitrary head hash S; the append (reading S as prev_hash) will compute
        # T = compute_record_hash(S, payload). Pre-seed a *lower-id* row already holding T so
        # the append's INSERT collides on UNIQUE(record_hash) and fails.
        head_hash = "S" * 64
        collision_target = compute_record_hash(head_hash, ev.hash_payload())

        # Row with the collision target (id 1) — must NOT be the chain head.
        session.execute(
            text(
                "INSERT INTO audit_log "
                "(prev_hash, record_hash, actor_id, actor_role, tenant_id, action, "
                " entity_type, entity_id, occurred_at) "
                "VALUES ('', :h, 'seed0', 'seed', 'seed', 'seed', 'seed', 'seed', now())"
            ),
            {"h": collision_target},
        )
        # Chain head (id 2) holding head_hash -> append reads this as prev_hash.
        session.execute(
            text(
                "INSERT INTO audit_log "
                "(prev_hash, record_hash, actor_id, actor_role, tenant_id, action, "
                " entity_type, entity_id, occurred_at) "
                "VALUES (:p, :h, 'seed1', 'seed', 'seed', 'seed', 'seed', 'seed', now())"
            ),
            {"p": collision_target, "h": head_hash},
        )
        session.commit()  # seed rows are committed; the txn under test starts clean

        # Business write in the same open transaction as the (about-to-fail) audit write.
        session.execute(text("INSERT INTO business_write (id) VALUES (1)"))

        with pytest.raises(IntegrityError):
            append_audit(session, ev)  # duplicate record_hash -> INSERT fails on flush

        # Caller observes the failure and rolls back the whole transaction (D-05).
        session.rollback()

        # The business write must NOT have persisted — atomic with the failed audit write.
        remaining = session.execute(text("SELECT count(*) FROM business_write")).scalar_one()
        assert remaining == 0
    finally:
        session.rollback()
        session.execute(text("DROP TABLE IF EXISTS business_write"))
        session.commit()
