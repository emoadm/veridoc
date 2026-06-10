"""Deterministic pseudonym tests (D-12, plan 01-03 Task 3).

The pseudonym shares the per-patient key hierarchy with veridoc-crypto (Pitfall 3 —
no separate global pseudonym key, no re-identification lookup table). Behavior:

- pseudonym_token(patient, natural_id) is deterministic: same inputs -> same token.
- Different patients (different derived keys) -> different tokens for the same natural_id.
- After veridoc_crypto.erase_patient(patient), the token can no longer be recomputed
  (the per-patient key is gone) — erasure makes the token irrecoverable (crypto-shred).
"""

import pytest
from veridoc_crypto import encrypt_field, erase_patient
from veridoc_crypto.keys import KeyErasedError, reset_keystore
from veridoc_pseudonym import pseudonym_token


@pytest.fixture(autouse=True)
def _fresh_keystore():
    reset_keystore()
    yield
    reset_keystore()


def test_token_is_deterministic_across_calls():
    t1 = pseudonym_token("patient-A", "MRN-12345")
    t2 = pseudonym_token("patient-A", "MRN-12345")
    assert t1 == t2
    assert isinstance(t1, str) and len(t1) == 64  # HMAC-SHA256 hex digest


def test_token_distinct_across_patients():
    # Same natural_id, different patients => different tokens (per-patient key isolation).
    ta = pseudonym_token("patient-A", "MRN-12345")
    tb = pseudonym_token("patient-B", "MRN-12345")
    assert ta != tb


def test_token_distinct_across_natural_ids():
    t1 = pseudonym_token("patient-A", "MRN-1")
    t2 = pseudonym_token("patient-A", "MRN-2")
    assert t1 != t2


def test_token_irrecomputable_after_erasure():
    # The token is stable before erasure ...
    before = pseudonym_token("patient-A", "MRN-12345")
    assert before == pseudonym_token("patient-A", "MRN-12345")

    erase_patient("patient-A")

    # ... and irrecomputable after (key gone => fail closed).
    with pytest.raises(KeyErasedError):
        pseudonym_token("patient-A", "MRN-12345")


def test_erasure_isolated_other_patient_token_intact():
    tb_before = pseudonym_token("patient-B", "MRN-999")
    erase_patient("patient-A")
    # B's token is unaffected by A's erasure (no global key).
    assert pseudonym_token("patient-B", "MRN-999") == tb_before


def test_pseudonym_shares_key_with_encryption():
    # Encrypting under patient A and erasing must also kill A's pseudonym — proving
    # both derive from ONE per-patient key (shared hierarchy, not separate keys).
    encrypt_field("patient-A", "PHI")
    _ = pseudonym_token("patient-A", "MRN-12345")
    erase_patient("patient-A")
    with pytest.raises(KeyErasedError):
        pseudonym_token("patient-A", "MRN-12345")
