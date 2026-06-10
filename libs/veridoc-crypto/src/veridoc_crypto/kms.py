"""Provider-portable KMS/HSM abstraction (D-11, plan 01-03 Task 2).

The KMS abstraction wraps/unwraps per-field Data Encryption Keys (DEKs) using a
*wrapping key*. In VeriDoc the wrapping key is the **per-patient key** (keys.py),
so a DEK is only recoverable while that patient's key can be derived — deleting the
patient's derivation material (crypto-shred) renders the wrapped DEK permanently
unrecoverable.

Wrapping is itself AES-256-GCM (Google Tink AEAD) built from the raw wrapping key —
we never hand-roll key wrapping. ``LocalKeyring`` is the in-process implementation
used by the tests (no cloud account needed); ``AwsKmsKeyring`` and
``AzureKeyVaultKeyring`` are interface stubs for when DEC-cloud-provider closes.
"""

from __future__ import annotations

import abc

import tink
from tink import aead, secret_key_access
from tink.proto import aes_gcm_pb2, tink_pb2

__all__ = [
    "KMSKeyring",
    "LocalKeyring",
    "AwsKmsKeyring",
    "AzureKeyVaultKeyring",
    "aead_from_raw_key",
]

aead.register()

_AES_GCM_TYPE_URL = "type.googleapis.com/google.crypto.tink.AesGcmKey"


def aead_from_raw_key(raw_key: bytes) -> aead.Aead:
    """Build a deterministic Tink AES-256-GCM AEAD primitive from a raw 32-byte key.

    This lets the per-patient key (an HKDF output) act as the DEK-wrapping key via
    Tink's vetted AEAD, instead of a hand-rolled AES call.
    """
    if len(raw_key) != 32:
        raise ValueError("AES-256-GCM wrapping key must be 32 bytes")
    gcm = aes_gcm_pb2.AesGcmKey(version=0, key_value=raw_key)
    key_data = tink_pb2.KeyData(
        type_url=_AES_GCM_TYPE_URL,
        value=gcm.SerializeToString(),
        key_material_type=tink_pb2.KeyData.SYMMETRIC,
    )
    keyset = tink_pb2.Keyset(
        primary_key_id=1,
        key=[
            tink_pb2.Keyset.Key(
                key_data=key_data,
                status=tink_pb2.ENABLED,
                key_id=1,
                output_prefix_type=tink_pb2.RAW,
            )
        ],
    )
    handle = tink.proto_keyset_format.parse(keyset.SerializeToString(), secret_key_access.TOKEN)
    return handle.primitive(aead.Aead)


class KMSKeyring(abc.ABC):
    """Provider-portable KMS interface: wrap/unwrap a DEK with a wrapping key.

    Implementations: LocalKeyring (tests), AwsKmsKeyring, AzureKeyVaultKeyring.
    The wrapping key is supplied per-call (the per-patient key) so a single keyring
    instance serves every patient without holding per-patient state.
    """

    @abc.abstractmethod
    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        """Encrypt (wrap) a DEK under the wrapping key; returns the wrapped DEK."""

    @abc.abstractmethod
    def unwrap_dek(self, wrapping_key: bytes, wrapped: bytes, aad: bytes = b"") -> bytes:
        """Decrypt (unwrap) a wrapped DEK under the wrapping key; returns the DEK."""


class LocalKeyring(KMSKeyring):
    """In-process keyring for tests/local dev — no cloud account required.

    Wraps the DEK with Tink AES-256-GCM keyed by the per-patient wrapping key.
    """

    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        return aead_from_raw_key(wrapping_key).encrypt(dek, aad)

    def unwrap_dek(self, wrapping_key: bytes, wrapped: bytes, aad: bytes = b"") -> bytes:
        return aead_from_raw_key(wrapping_key).decrypt(wrapped, aad)


class AwsKmsKeyring(KMSKeyring):  # pragma: no cover - interface stub (no live calls)
    """AWS KMS adapter (interface only this phase; DEC-cloud-provider OPEN).

    When DEC-cloud-provider closes to AWS, this wires Tink's AWS KMS integration so
    the DEK is wrapped by a KMS-resident key reference instead of a local key.
    """

    def __init__(self, key_arn: str) -> None:
        self.key_arn = key_arn

    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        raise NotImplementedError(
            "AwsKmsKeyring is a portability stub this phase; wire Tink AWS KMS "
            "when DEC-cloud-provider closes to AWS"
        )

    def unwrap_dek(self, wrapping_key: bytes, wrapped: bytes, aad: bytes = b"") -> bytes:
        raise NotImplementedError(
            "AwsKmsKeyring is a portability stub this phase; wire Tink AWS KMS "
            "when DEC-cloud-provider closes to AWS"
        )


class AzureKeyVaultKeyring(KMSKeyring):  # pragma: no cover - interface stub
    """Azure Key Vault adapter (interface only this phase; DEC-cloud-provider OPEN)."""

    def __init__(self, vault_url: str, key_name: str) -> None:
        self.vault_url = vault_url
        self.key_name = key_name

    def wrap_dek(self, wrapping_key: bytes, dek: bytes, aad: bytes = b"") -> bytes:
        raise NotImplementedError(
            "AzureKeyVaultKeyring is a portability stub this phase; wire Tink Azure "
            "Key Vault when DEC-cloud-provider closes to Azure"
        )

    def unwrap_dek(self, wrapping_key: bytes, wrapped: bytes, aad: bytes = b"") -> bytes:
        raise NotImplementedError(
            "AzureKeyVaultKeyring is a portability stub this phase; wire Tink Azure "
            "Key Vault when DEC-cloud-provider closes to Azure"
        )
