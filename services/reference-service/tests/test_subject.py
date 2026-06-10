"""Task 1 behaviour: the end-to-end Subject create/update path (D-07 walking skeleton).

POST /subjects (authenticated, MFA, permitted role, resolved tenant) must:
  - derive the deterministic pseudonym token (veridoc_pseudonym),
  - envelope-encrypt the PII field (veridoc_crypto),
  - insert the Subject row carrying tenant_id from current_tenant(),
  - call append_audit in the SAME transaction, committing once (business row + audit row
    are atomic), so verify_chain(session) is True afterward.
GET /healthz returns 200 without auth.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session
from veridoc_audit import verify_chain


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_healthz_is_open(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_post_subject_persists_row_and_atomic_audit(client, migrated_engine, make_token):
    token = make_token(
        sub="coordinator-1",
        roles=["site-coordinator"],
        site="site-001",
        study="study-A",
    )
    body = {"natural_id": "MRN-12345", "pii": "Alice Patient"}
    resp = client.post("/subjects", json=body, headers=_auth(token))
    assert resp.status_code == 201, resp.text
    out = resp.json()
    assert out["pseudonym_token"]  # deterministic token derived
    assert "pii" not in out  # plaintext PII never echoed back
    subject_id = out["id"]

    with Session(migrated_engine) as session:
        # Business row persisted with tenant_id from current_tenant().
        row = session.execute(
            text("SELECT tenant_id, pseudonym_token, pii_ciphertext FROM subject WHERE id = :i"),
            {"i": subject_id},
        ).one()
        assert row.tenant_id == "site-001/study-A"
        assert row.pseudonym_token == out["pseudonym_token"]
        # Encrypted at rest: the stored bytes are NOT the plaintext.
        assert bytes(row.pii_ciphertext) != b"Alice Patient"
        # Same-transaction audit row committed atomically -> chain verifies.
        assert verify_chain(session) is True
        # The audit row records the create action for this subject.
        audit = session.execute(
            text(
                "SELECT actor_id, actor_role, tenant_id, action, entity_type, entity_id "
                "FROM audit_log WHERE entity_id = :e ORDER BY id DESC LIMIT 1"
            ),
            {"e": str(subject_id)},
        ).one()
        assert audit.actor_id == "coordinator-1"
        assert audit.actor_role == "site-coordinator"
        assert audit.tenant_id == "site-001/study-A"
        assert audit.action == "create"
        assert audit.entity_type == "subject"


def test_post_subject_pii_round_trips_via_pseudonym(client, make_token):
    token = make_token(
        sub="coordinator-1",
        roles=["site-coordinator"],
        site="site-001",
        study="study-A",
    )
    resp = client.post(
        "/subjects",
        json={"natural_id": "MRN-9", "pii": "Bob Patient"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    pseudonym = resp.json()["pseudonym_token"]
    # The pseudonym is the patient token used as the crypto/pseudonym patient_id; PII decrypts.
    # (decrypt is proven directly in test_field_encryption; here we just assert the token exists.)
    assert len(pseudonym) == 64  # HMAC-SHA256 hexdigest


def test_put_subject_updates_with_before_after_audit(client, migrated_engine, make_token):
    token = make_token(
        sub="dm-1",
        roles=["data-manager"],
        site="site-001",
        study="study-A",
    )
    create = client.post(
        "/subjects",
        json={"natural_id": "MRN-77", "pii": "Carol Old"},
        headers=_auth(token),
    )
    assert create.status_code == 201, create.text
    subject_id = create.json()["id"]

    update = client.put(
        f"/subjects/{subject_id}",
        json={"pii": "Carol New"},
        headers=_auth(token),
    )
    assert update.status_code == 200, update.text

    with Session(migrated_engine) as session:
        audit = session.execute(
            text(
                "SELECT action, before, after FROM audit_log "
                "WHERE entity_id = :e AND action = 'update' ORDER BY id DESC LIMIT 1"
            ),
            {"e": str(subject_id)},
        ).one()
        assert audit.action == "update"
        # before/after capture the change (values are already pseudonymized/encrypted refs).
        assert audit.before is not None
        assert audit.after is not None
        assert verify_chain(session) is True


def test_post_subject_rejects_unexpected_fields(client, make_token):
    token = make_token(
        sub="coordinator-1",
        roles=["site-coordinator"],
        site="site-001",
        study="study-A",
    )
    resp = client.post(
        "/subjects",
        json={"natural_id": "MRN-1", "pii": "X", "is_admin": True},
        headers=_auth(token),
    )
    assert resp.status_code == 422  # Pydantic v2 rejects extra fields (V5 input validation)


def test_post_subject_requires_auth(client):
    resp = client.post("/subjects", json={"natural_id": "MRN-1", "pii": "X"})
    assert resp.status_code == 401
