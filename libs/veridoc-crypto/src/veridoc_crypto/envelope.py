"""AES-256-GCM envelope field encryption (D-11, plan 01-03 Task 2).

App-level envelope encryption — NOT pgcrypto / DB-engine crypto (D-11 forbids it):

  encrypt_field(patient_id, plaintext):
    1. generate a fresh per-field DEK (32 bytes);
    2. AES-256-GCM (Google Tink AEAD) encrypt the plaintext with the DEK
       (random nonce ⇒ repeated encryptions of the same value are distinct);
    3. wrap the DEK with the per-patient key via the KMS abstraction (kms.wrap_dek);
    4. pack (wrapped_dek, field_ciphertext) for storage. Only ciphertext + wrapped
       DEK ever land at rest; plaintext keys never touch the DB engine (T-03-04).

  decrypt_field reverses it: unwrap the DEK with the per-patient key, then AES-256-GCM
  decrypt. If the patient has been crypto-shredded, the per-patient key can no longer
  be derived, so unwrap fails and decryption is impossible (KeyErasedError) — the GDPR
  Art. 17 erasure guarantee.
"""

from __future__ import annotations

import secrets
import struct

from . import keys
from .kms import KMSKeyring, LocalKeyring, aead_from_raw_key

__all__ = ["encrypt_field", "decrypt_field", "erase_patient"]

# Bind the wrapped DEK to the patient so a DEK wrapped for A can't be unwrapped for B.
_DEK_LEN = 32  # AES-256
_VERSION = 1

# Default keyring is the local, no-cloud-account keyring (DEC-cloud-provider OPEN).
_default_keyring: KMSKeyring = LocalKeyring()


def _pack(wrapped_dek: bytes, field_ct: bytes) -> bytes:
    """version || len(wrapped_dek) || wrapped_dek || field_ciphertext."""
    return struct.pack(">BI", _VERSION, len(wrapped_dek)) + wrapped_dek + field_ct


def _unpack(blob: bytes) -> tuple[bytes, bytes]:
    version, wlen = struct.unpack(">BI", blob[:5])
    if version != _VERSION:
        raise ValueError(f"unsupported envelope version {version}")
    wrapped_dek = blob[5 : 5 + wlen]
    field_ct = blob[5 + wlen :]
    return wrapped_dek, field_ct


def encrypt_field(patient_id: str, plaintext: str, *, keyring: KMSKeyring | None = None) -> bytes:
    """Envelope-encrypt a PII field for ``patient_id``; returns packed ciphertext bytes.

    Raises :class:`veridoc_crypto.keys.KeyErasedError` if the patient is erased.
    """
    keyring = keyring or _default_keyring
    patient_key = keys.get_patient_key(patient_id)  # raises if erased

    dek = secrets.token_bytes(_DEK_LEN)
    aad = patient_id.encode("utf-8")
    field_ct = aead_from_raw_key(dek).encrypt(plaintext.encode("utf-8"), aad)
    wrapped_dek = keyring.wrap_dek(patient_key, dek, aad)
    return _pack(wrapped_dek, field_ct)


def decrypt_field(patient_id: str, ciphertext: bytes, *, keyring: KMSKeyring | None = None) -> str:
    """Decrypt a packed envelope ciphertext for ``patient_id``; returns the plaintext.

    Raises :class:`veridoc_crypto.keys.KeyErasedError` if the patient is erased
    (the DEK can no longer be unwrapped). A ciphertext encrypted under a different
    patient (or otherwise tampered) fails the AEAD check and raises.
    """
    keyring = keyring or _default_keyring
    patient_key = keys.get_patient_key(patient_id)  # raises KeyErasedError if erased

    wrapped_dek, field_ct = _unpack(ciphertext)
    aad = patient_id.encode("utf-8")
    dek = keyring.unwrap_dek(patient_key, wrapped_dek, aad)
    return aead_from_raw_key(dek).decrypt(field_ct, aad).decode("utf-8")


# Re-export erasure so callers can crypto-shred via the crypto package directly.
erase_patient = keys.erase_patient
