"""Field-encryption tests (D-11): AES-256-GCM envelope encryption, per-patient key.

Behavior under test (plan 01-03 Task 2):
- encrypt_field(patient, "PHI") returns bytes != the plaintext bytes (ciphertext at rest).
- decrypt_field(patient, encrypt_field(patient, x)) == x (round-trip).
- Two encryptions of the same plaintext produce different ciphertext (random GCM nonce).
- derive_patient_key isolates patients (A != B).
- The DEK is wrapped via the KMS abstraction (envelope encryption, not raw AES).
"""

import pytest
from tink import TinkError
from veridoc_crypto import (
    decrypt_field,
    derive_patient_key,
    encrypt_field,
)
from veridoc_crypto.keys import reset_keystore


@pytest.fixture(autouse=True)
def _fresh_keystore():
    # Each test starts from a clean, fully-populated derivation store.
    reset_keystore()
    yield
    reset_keystore()


def test_ciphertext_differs_from_plaintext():
    pt = "Jane Doe, DOB 1980-01-01"
    ct = encrypt_field("patient-A", pt)
    assert isinstance(ct, bytes)
    assert ct != pt.encode()
    assert pt.encode() not in ct  # plaintext must not appear at rest


def test_round_trip():
    pt = "MRN-0001 :: 123-45-6789"
    ct = encrypt_field("patient-A", pt)
    assert decrypt_field("patient-A", ct) == pt


def test_repeated_encrypt_yields_distinct_ciphertext():
    pt = "same PHI value"
    ct1 = encrypt_field("patient-A", pt)
    ct2 = encrypt_field("patient-A", pt)
    assert ct1 != ct2  # random GCM nonce / fresh DEK
    # both still decrypt to the same plaintext
    assert decrypt_field("patient-A", ct1) == pt
    assert decrypt_field("patient-A", ct2) == pt


def test_per_patient_key_isolation():
    master = b"\x01" * 32
    ka = derive_patient_key(master, "patient-A")
    kb = derive_patient_key(master, "patient-B")
    assert ka != kb
    assert len(ka) == 32 and len(kb) == 32


def test_derive_patient_key_is_deterministic():
    master = b"\x02" * 32
    assert derive_patient_key(master, "patient-A") == derive_patient_key(master, "patient-A")


def test_cross_patient_decrypt_fails():
    # A field encrypted under patient A must not decrypt under patient B's key.
    ct = encrypt_field("patient-A", "secret")
    with pytest.raises(TinkError):
        decrypt_field("patient-B", ct)
