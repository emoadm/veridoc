"""GDPR Art. 17 erasure × 21 CFR Part 11 immutability — the phase's hardest seam (T-05-08).

Create Subject A and Subject B (each write produces an audit row whose ``after`` jsonb carries
that patient's pseudonym token + the envelope ciphertext payload). Then crypto-shred patient A
via ``veridoc_crypto.erase_patient``. After erasure, the COMBINED invariant must hold:

1. ``verify_chain(session)`` STILL returns True — the append-only audit rows are immutable and
   untouched; only A's per-patient key is gone (erasure must NOT mutate/delete Part 11 rows);
2. A's audited PII payload (the ciphertext stored in A's audit row) is no longer decryptable —
   ``decrypt_field(A, that_ciphertext)`` raises;
3. patient B is fully unaffected — B's ciphertext still decrypts AND B's pseudonym still
   recomputes to the same value.
"""

from __future__ import annotations

import base64

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from veridoc_crypto import decrypt_field, erase_patient
from veridoc_crypto.keys import KeyErasedError
from veridoc_pseudonym import pseudonym_token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create(client, make_token, *, natural_id, pii):
    token = make_token(sub="coord", roles=["site-coordinator"], site="site-001", study="study-A")
    resp = client.post(
        "/subjects",
        json={"natural_id": natural_id, "pii": pii},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _audited_ciphertext(session: Session, *, pseudonym: str) -> bytes:
    """Pull the envelope ciphertext that the create audit row captured for this patient."""
    row = session.execute(
        text(
            "SELECT after FROM audit_log "
            "WHERE entity_type = 'subject' AND action = 'create' "
            "AND after->>'pseudonym_token' = :p ORDER BY id DESC LIMIT 1"
        ),
        {"p": pseudonym},
    ).scalar_one()
    return base64.b64decode(row["pii_ciphertext_b64"])


def test_erase_A_keeps_chain_immutable_A_undecryptable_B_intact(
    client, migrated_engine, make_token
):
    a = _create(client, make_token, natural_id="PATIENT-A", pii="Alice Secret")
    b = _create(client, make_token, natural_id="PATIENT-B", pii="Bob Secret")
    token_a = a["pseudonym_token"]
    token_b = b["pseudonym_token"]

    with Session(migrated_engine) as session:
        ct_a = _audited_ciphertext(session, pseudonym=token_a)
        ct_b = _audited_ciphertext(session, pseudonym=token_b)
        # Pre-condition: both decrypt and the chain is intact.
        assert decrypt_field(token_a, ct_a) == "Alice Secret"
        assert decrypt_field(token_b, ct_b) == "Bob Secret"
        assert verify_chain_ok(session)

    # Crypto-shred patient A (the crypto patient_id at rest is the pseudonym token).
    erase_patient(token_a)

    with Session(migrated_engine) as session:
        # (1) The append-only audit chain STILL verifies — rows were never mutated/deleted.
        assert verify_chain_ok(session)

        # (2) A's audited ciphertext is no longer decryptable (key crypto-shredded).
        with pytest.raises(KeyErasedError):
            decrypt_field(token_a, ct_a)

        # (3) B is fully unaffected: ciphertext still decrypts AND pseudonym still recomputes.
        assert decrypt_field(token_b, ct_b) == "Bob Secret"
        assert pseudonym_token("PATIENT-B", "PATIENT-B") == token_b


def verify_chain_ok(session: Session) -> bool:
    from veridoc_audit import verify_chain

    return verify_chain(session) is True
