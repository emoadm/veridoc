"""PII is encrypted at rest, not stored as plaintext (T-05-04).

After POST /subjects, the raw ``pii_ciphertext`` column read directly via SQL does NOT equal
the submitted plaintext, and ``decrypt_field`` round-trips it back to the plaintext under the
subject's pseudonym token (the crypto patient_id).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session
from veridoc_crypto import decrypt_field


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_pii_is_ciphertext_at_rest_and_round_trips(client, migrated_engine, make_token):
    plaintext = "Jane Q. Patient, DOB 1980-01-01"
    token = make_token(
        sub="coord", roles=["site-coordinator"], site="site-001", study="study-A"
    )
    resp = client.post(
        "/subjects",
        json={"natural_id": "MRN-ENC", "pii": plaintext},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    pseudonym = resp.json()["pseudonym_token"]
    subject_id = resp.json()["id"]

    with Session(migrated_engine) as session:
        raw = session.execute(
            text("SELECT pii_ciphertext FROM subject WHERE id = :i"),
            {"i": subject_id},
        ).scalar_one()
        raw_bytes = bytes(raw)

    # At rest: the stored bytes are ciphertext, NOT the submitted plaintext.
    assert raw_bytes != plaintext.encode("utf-8")
    assert plaintext.encode("utf-8") not in raw_bytes

    # The crypto layer round-trips the ciphertext back to plaintext under the pseudonym token.
    assert decrypt_field(pseudonym, raw_bytes) == plaintext
