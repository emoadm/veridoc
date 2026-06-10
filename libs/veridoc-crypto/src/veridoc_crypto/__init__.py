"""veridoc_crypto — app-level envelope encryption + per-patient key hierarchy (D-11/D-12).

Implemented in plan 01-03: AES-256-GCM envelope encryption (Google Tink AEAD) behind a
provider-portable KMS abstraction, with a master-key + per-patient HKDF-derived key
hierarchy. GDPR right-to-erasure (Art. 17) is crypto-shredding — deleting one patient's
derivation material makes their ciphertext undecryptable and their pseudonym irrecomputable
without touching other patients (see docs/validation/KEY-HIERARCHY.md).

Public API (consumed by veridoc_pseudonym and plan 01-05 reference service):
    encrypt_field(patient_id, plaintext) -> bytes      # envelope ciphertext at rest
    decrypt_field(patient_id, ciphertext) -> str       # round-trip
    erase_patient(patient_id) -> None                  # crypto-shred (GDPR Art. 17)
    derive_patient_key(master, patient_id) -> bytes    # HKDF per-patient derivation
    get_patient_key(patient_id) -> bytes               # derive via the master keystore
    patient_key_exists(patient_id) -> bool
"""

from .envelope import decrypt_field, encrypt_field, erase_patient
from .keys import (
    KeyErasedError,
    derive_patient_key,
    get_patient_key,
    patient_key_exists,
)
from .kms import (
    AwsKmsKeyring,
    AzureKeyVaultKeyring,
    KMSKeyring,
    LocalKeyring,
)

__all__ = [
    "encrypt_field",
    "decrypt_field",
    "erase_patient",
    "derive_patient_key",
    "get_patient_key",
    "patient_key_exists",
    "KeyErasedError",
    "KMSKeyring",
    "LocalKeyring",
    "AwsKmsKeyring",
    "AzureKeyVaultKeyring",
]
