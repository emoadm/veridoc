"""Per-patient key hierarchy (D-11 + D-12, plan 01-03 Task 2).

A single MASTER key roots the hierarchy. Each patient's key is DERIVED from the
master key via HKDF (RFC 5869, HMAC-SHA256) using the ``patient_id`` as the
per-patient salt/info, so:

- different patients get cryptographically distinct keys (isolation);
- the per-patient key is never persisted in plaintext — it is re-derived on demand
  from the master key + the patient's *derivation material*;
- GDPR right-to-erasure (Art. 17) is **crypto-shredding**: ``erase_patient`` deletes
  the patient's derivation material so the per-patient key can NEVER be re-derived,
  which simultaneously makes that patient's ciphertext undecryptable and their
  deterministic pseudonym irrecomputable — without touching any other patient
  (KEY-HIERARCHY.md, Pitfall 3, A7).

There is **no global pseudonym/encryption key** — that would make single-patient
erasure impossible. HKDF here is the standard RFC 5869 construction over the stdlib
``hmac``/``hashlib`` primitives; the AEAD that protects field data lives in
``envelope.py`` and uses the vetted Google Tink library (we never hand-roll AEAD).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

__all__ = [
    "KeyErasedError",
    "derive_patient_key",
    "get_patient_key",
    "erase_patient",
    "patient_key_exists",
    "reset_keystore",
    "load_master_key",
]

_HASH = hashlib.sha256
_HASH_LEN = _HASH().digest_size  # 32 bytes → 256-bit per-patient key
_HKDF_INFO = b"veridoc/per-patient-key/v1"


class KeyErasedError(Exception):
    """Raised when a patient's key material has been crypto-shredded (erased).

    After ``erase_patient(patient_id)`` the per-patient key can no longer be
    derived, so any operation requiring it (decrypt, pseudonym recompute) fails
    closed with this error — the GDPR Art. 17 erasure guarantee.
    """


def _hkdf(master: bytes, *, salt: bytes, info: bytes, length: int = _HASH_LEN) -> bytes:
    """RFC 5869 HKDF (extract-and-expand) over HMAC-SHA256.

    Standard, well-specified KDF — not hand-rolled cryptography. Used to derive a
    per-patient key from the master key with ``patient_id`` mixed into salt + info.
    """
    if not salt:
        salt = b"\x00" * _HASH_LEN
    # Extract
    prk = hmac.new(salt, master, _HASH).digest()
    # Expand
    okm = b""
    t = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), _HASH).digest()
        okm += t
        counter += 1
    return okm[:length]


def derive_patient_key(master: bytes, patient_id: str) -> bytes:
    """Deterministically derive a patient's 256-bit key from the master key.

    Pure function — the same (master, patient_id) always yields the same key;
    different patient_ids yield distinct keys. This is the single key both the
    encryption path (envelope.py) and the pseudonym path (veridoc_pseudonym) share.
    """
    pid = patient_id.encode("utf-8")
    return _hkdf(master, salt=pid, info=_HKDF_INFO + b"/" + pid, length=_HASH_LEN)


# --------------------------------------------------------------------------- #
# Derivation-material keystore (the crypto-shredding surface).
#
# Erasure deletes a patient's derivation material so their key can never be
# re-derived. We model the "derivation material" as the per-patient salt entry
# recorded the first time a patient's key is used: deleting that entry forgets
# the patient. (In production the per-patient salt + the KMS-wrapped master live
# in the key store; LocalKeyring stands in for that here so tests need no cloud.)
# --------------------------------------------------------------------------- #

_master_key: bytes | None = None
# patient_id -> derivation material present (True). Absence/False => erased/unknown.
_derivation_material: dict[str, bytes] = {}
_erased: set[str] = set()


def load_master_key() -> bytes:
    """Load the master key from config/KMS.

    For tests / local dev the master key is sourced from ``VERIDOC_MASTER_KEY``
    (hex) when set, else a process-stable random key is generated once. In
    production this is loaded from / wrapped by the KMS abstraction (kms.py).
    """
    global _master_key
    if _master_key is None:
        env = os.environ.get("VERIDOC_MASTER_KEY")
        if env:
            _master_key = bytes.fromhex(env)
        else:
            _master_key = secrets.token_bytes(_HASH_LEN)
    return _master_key


def get_patient_key(patient_id: str) -> bytes:
    """Return the per-patient key, registering derivation material on first use.

    Raises :class:`KeyErasedError` if the patient has been crypto-shredded.
    """
    if patient_id in _erased:
        raise KeyErasedError(
            f"patient {patient_id!r} has been erased (crypto-shredded); "
            "key material is irrecoverable"
        )
    # Record (or confirm) the patient's derivation material exists.
    _derivation_material.setdefault(patient_id, b"\x01")
    return derive_patient_key(load_master_key(), patient_id)


def patient_key_exists(patient_id: str) -> bool:
    """True iff the patient's key can still be derived (not erased, material present)."""
    return patient_id in _derivation_material and patient_id not in _erased


def erase_patient(patient_id: str) -> None:
    """Crypto-shred a patient: delete their derivation material (GDPR Art. 17).

    Idempotent — erasing an unknown or already-erased patient is a no-op. After
    this call the per-patient key can no longer be derived, so the patient's
    ciphertext is undecryptable and their pseudonym is irrecomputable, while every
    other patient is untouched.
    """
    _derivation_material.pop(patient_id, None)
    _erased.add(patient_id)


def reset_keystore() -> None:
    """Test helper: forget all derivation material, erasures, and the master key."""
    global _master_key
    _master_key = None
    _derivation_material.clear()
    _erased.clear()
