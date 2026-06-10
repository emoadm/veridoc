"""Every login attempt — success AND failure — produces an audit record.

A successful authenticated request and a rejected one (missing/insufficient MFA) must each
leave an immutable audit row capturing the login outcome (21 CFR Part 11 / Annex 11 access
logging). The audit row's hash chain still verifies after both.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session
from veridoc_audit import verify_chain


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login_rows(session: Session, *, action: str) -> list:
    return session.execute(
        text(
            "SELECT actor_id, action, tenant_id FROM audit_log "
            "WHERE entity_type = 'auth' AND action = :a ORDER BY id"
        ),
        {"a": action},
    ).all()


def test_successful_login_is_audited(client, migrated_engine, make_token):
    token = make_token(
        sub="user-success", roles=["site-coordinator"], site="site-001", study="study-A"
    )
    resp = client.post(
        "/subjects", json={"natural_id": "MRN-1", "pii": "P"}, headers=_auth(token)
    )
    assert resp.status_code == 201, resp.text

    with Session(migrated_engine) as session:
        rows = _login_rows(session, action="login-success")
        assert any(r.actor_id == "user-success" for r in rows)
        assert verify_chain(session) is True


def test_failed_login_is_audited(client, migrated_engine, make_token):
    # A token missing MFA is rejected (401) — but the attempt must still be audited.
    token = make_token(
        sub="user-fail",
        roles=["site-coordinator"],
        site="site-001",
        study="study-A",
        mfa=False,
    )
    resp = client.post(
        "/subjects", json={"natural_id": "MRN-2", "pii": "P"}, headers=_auth(token)
    )
    assert resp.status_code == 401

    with Session(migrated_engine) as session:
        rows = _login_rows(session, action="login-failure")
        assert len(rows) >= 1
        assert verify_chain(session) is True
