"""veridoc_pseudonym — deterministic per-patient pseudonymization (D-12).

Implemented in plan 01-03: ``pseudonym_token(patient_id, natural_id)`` =
HMAC-SHA256(per_patient_key, natural_id), where the per-patient key is derived from the
SAME master-key + HKDF hierarchy that veridoc_crypto uses for envelope encryption
(see docs/validation/KEY-HIERARCHY.md). Crypto-shredding erasure (veridoc_crypto.erase_patient)
makes the token irrecomputable — no separate global pseudonym key, no re-identification table.

Public API:
    pseudonym_token(patient_id, natural_id) -> str   # deterministic HMAC-SHA256 hex digest
"""

from .pseudonym import pseudonym_token

__all__ = ["pseudonym_token"]
