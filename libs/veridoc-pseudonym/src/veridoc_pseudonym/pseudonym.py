"""Deterministic per-patient pseudonym token (D-12, plan 01-03 Task 3).

    pseudonym_token(patient_id, natural_id)
      = HMAC-SHA256(derive_patient_key(master, patient_id), natural_id).hexdigest()

The token is deterministic (same inputs → same token, stable across EMR + Rave sources
for cross-source SDV matching), distinct across patients (each has a distinct derived
key) and across natural_ids, and **not reversible** without the per-patient key.

Crucially the per-patient key comes from ``veridoc_crypto.keys`` — the SAME key the
envelope-encryption path uses (KEY-HIERARCHY.md, Pitfall 3). There is no separate global
pseudonym key and no re-identification lookup table (D-12). Therefore GDPR right-to-erasure
is crypto-shredding: after ``veridoc_crypto.erase_patient(patient_id)`` the per-patient key
can no longer be derived, so the token is irrecomputable (``get_patient_key`` raises
``KeyErasedError``) — exactly as the patient's ciphertext becomes undecryptable.
"""

from __future__ import annotations

import hashlib
import hmac

from veridoc_crypto import get_patient_key

__all__ = ["pseudonym_token"]


def pseudonym_token(patient_id: str, natural_id: str) -> str:
    """Return the deterministic pseudonym token for ``natural_id`` under ``patient_id``.

    Raises :class:`veridoc_crypto.keys.KeyErasedError` if the patient has been
    crypto-shredded (the per-patient key is gone → the token is irrecomputable).
    """
    patient_key = get_patient_key(patient_id)  # shared hierarchy; raises if erased
    return hmac.new(patient_key, natural_id.encode("utf-8"), hashlib.sha256).hexdigest()
