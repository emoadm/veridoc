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

__all__ = ["pseudonym_token", "patient_key_namespace", "patient_pseudonym"]


def pseudonym_token(patient_id: str, natural_id: str) -> str:
    """Return the deterministic pseudonym token for ``natural_id`` under ``patient_id``.

    Raises :class:`veridoc_crypto.keys.KeyErasedError` if the patient has been
    crypto-shredded (the per-patient key is gone → the token is irrecomputable).
    """
    patient_key = get_patient_key(patient_id)  # shared hierarchy; raises if erased
    return hmac.new(patient_key, natural_id.encode("utf-8"), hashlib.sha256).hexdigest()


def patient_key_namespace(site_id: str, natural_id: str) -> str:
    """Return the canonical per-patient key-namespace string (CR-05).

    The first argument to :func:`pseudonym_token` selects the *per-patient* crypto
    key (``get_patient_key``). For per-patient crypto-shredding (D-14) and
    cross-source matching (SC-4) to both hold, every adapter MUST derive that
    namespace identically as ``f"{site_id}-{natural_id}"`` — never just the
    ``site_id`` (which would share one key across all patients at the site and
    defeat per-patient erasure) and never an adapter-specific scheme (which would
    break cross-source linkage of the same physical patient).

    This is the single canonical definition; all four adapters call it so the
    derivation can never drift between modalities.
    """
    return f"{site_id}-{natural_id}"


def patient_pseudonym(site_id: str, natural_id: str) -> str:
    """Return the canonical patient pseudonym token for a ``(site_id, natural_id)`` pair.

    Convenience wrapper that applies the canonical per-patient key-namespace
    (:func:`patient_key_namespace`) and then :func:`pseudonym_token`. Using this
    one entry point in every adapter guarantees that the same physical patient —
    arriving via native-FHIR, HL7v2, PDF/Excel, or OCR — produces the SAME token
    (SC-4), while distinct patients at the same site get distinct, independently
    erasable keys (D-14).
    """
    namespace = patient_key_namespace(site_id, natural_id)
    return pseudonym_token(namespace, natural_id)
