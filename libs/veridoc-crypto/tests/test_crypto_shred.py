"""Crypto-shredding tests (D-12, GDPR Art. 17): erasure = delete derivation material.

Behavior under test (plan 01-03 Task 2):
- After erase_patient(A), decrypt_field(A, prior_ciphertext) raises (undecryptable).
- After erase_patient(A), the per-patient key can no longer be derived (irrecomputable).
- Patient B is unaffected: B's ciphertext still round-trips after A is erased.
- No global key: erasing one patient does not touch any other patient.
"""

import pytest

from veridoc_crypto import (
    decrypt_field,
    encrypt_field,
    erase_patient,
    patient_key_exists,
)
from veridoc_crypto.keys import KeyErasedError, reset_keystore


@pytest.fixture(autouse=True)
def _fresh_keystore():
    reset_keystore()
    yield
    reset_keystore()


def test_erase_makes_ciphertext_undecryptable():
    ct_a = encrypt_field("patient-A", "A's PHI")
    assert decrypt_field("patient-A", ct_a) == "A's PHI"  # works before erasure

    erase_patient("patient-A")

    with pytest.raises(KeyErasedError):
        decrypt_field("patient-A", ct_a)


def test_erase_makes_key_irrecomputable():
    encrypt_field("patient-A", "x")
    assert patient_key_exists("patient-A") is True
    erase_patient("patient-A")
    assert patient_key_exists("patient-A") is False


def test_erasure_is_isolated_other_patients_intact():
    ct_a = encrypt_field("patient-A", "A's PHI")
    ct_b = encrypt_field("patient-B", "B's PHI")

    erase_patient("patient-A")

    # A is shredded ...
    with pytest.raises(KeyErasedError):
        decrypt_field("patient-A", ct_a)
    # ... but B is completely unaffected.
    assert decrypt_field("patient-B", ct_b) == "B's PHI"
    assert patient_key_exists("patient-B") is True


def test_erasing_unknown_patient_is_idempotent():
    # Erasing a patient that was never written (or already erased) must not raise.
    erase_patient("never-seen")
    erase_patient("patient-A")
    erase_patient("patient-A")
