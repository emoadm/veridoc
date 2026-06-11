"""Proprietary-API adapter — interface stub (D-11).

This adapter conforms to :class:`SourceAdapter` but raises
:exc:`NotImplementedError` on every call. It exists to satisfy the SourceAdapter
protocol and allow the registry to route PROPRIETARY-modality sites without
failing at startup.

Pattern: mirrors AwsKmsKeyring / AzureKeyVaultKeyring in veridoc-crypto/kms.py —
the stub class is the interface placeholder for a cloud/vendor capability that is
not yet available.

When a real proprietary vendor contract is available for testing, replace the body
of :meth:`ingest` with the vendor-API integration and remove the
``# pragma: no cover`` annotation.
"""

from __future__ import annotations

from ..adapter import SourceAdapter, SourceProfile

__all__ = ["ProprietaryAdapter"]


class ProprietaryAdapter(SourceAdapter):  # pragma: no cover - no real contract to test (D-11)
    """Proprietary-API adapter (interface stub this milestone; D-11).

    When a real proprietary vendor contract is available for testing, this class
    wires the vendor API so the PROPRIETARY modality becomes fully operational.
    """

    def ingest(self, payload: bytes, profile: SourceProfile) -> list:
        raise NotImplementedError(
            "ProprietaryAdapter is an interface stub this phase; wire the vendor API "
            "when a proprietary contract is available for testing (D-11)"
        )
