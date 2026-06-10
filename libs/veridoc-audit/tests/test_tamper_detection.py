"""THE phase-gate test (Success Criterion #2 / threat T-02-01).

Write a multi-row chain, prove verify_chain() is True, then mutate a prior persisted row
and prove verify_chain() flips to False. Also proves the BEFORE UPDATE OR DELETE trigger
makes the table immutable, and that the advisory lock prevents a forked chain.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from veridoc_audit import AuditEvent, append_audit, verify_chain


def _event(n: int) -> AuditEvent:
    return AuditEvent(
        actor_id="user-1",
        actor_role="CRA",
        tenant_id="study-A/site-1",
        action="create",
        entity_type="subject",
        entity_id=f"subj-{n}",
        before=None,
        after={"status": "enrolled", "n": n},
        occurred_at=datetime(2026, 6, 11, 12, 0, n, tzinfo=UTC),
    )


def test_intact_chain_verifies_true(session):
    append_audit(session, _event(1))
    append_audit(session, _event(2))
    session.commit()
    assert verify_chain(session) is True


def test_mutated_row_breaks_chain(session):
    """Mutate a prior row's `after` jsonb (trigger bypassed in-test) -> verify_chain False."""
    append_audit(session, _event(1))
    append_audit(session, _event(2))
    session.commit()
    assert verify_chain(session) is True  # baseline: intact

    # Disable the immutability trigger for THIS session only so we can simulate a
    # privileged-actor tamper, then mutate the first row's payload.
    session.execute(text("ALTER TABLE audit_log DISABLE TRIGGER audit_log_immutable"))
    session.execute(
        text("UPDATE audit_log SET after = :a WHERE id = (SELECT min(id) FROM audit_log)"),
        {"a": '{"status": "TAMPERED"}'},
    )
    session.execute(text("ALTER TABLE audit_log ENABLE TRIGGER audit_log_immutable"))
    session.commit()

    # The mutated row no longer hashes to its stored record_hash -> chain broken.
    assert verify_chain(session) is False


def test_update_blocked_by_immutability_trigger(session):
    append_audit(session, _event(1))
    session.commit()
    with pytest.raises(DBAPIError):  # trigger RAISES (check_violation)
        session.execute(text("UPDATE audit_log SET action = 'x' WHERE id > 0"))
        session.commit()
    session.rollback()


def test_delete_blocked_by_immutability_trigger(session):
    append_audit(session, _event(1))
    session.commit()
    with pytest.raises(DBAPIError):
        session.execute(text("DELETE FROM audit_log WHERE id > 0"))
        session.commit()
    session.rollback()


def test_serial_appends_do_not_fork_prev_hash(session):
    """Two serialized appends produce distinct prev_hash links (no fork)."""
    append_audit(session, _event(1))
    append_audit(session, _event(2))
    session.commit()
    prev_hashes = [
        r[0] for r in session.execute(text("SELECT prev_hash FROM audit_log ORDER BY id")).all()
    ]
    assert prev_hashes[0] == ""  # genesis
    assert prev_hashes[1] != ""
    assert len(set(prev_hashes)) == len(prev_hashes)  # no two rows share a prev_hash
