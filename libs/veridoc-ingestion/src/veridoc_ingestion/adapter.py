"""Ingestion contract: SourceAdapter ABC, SourceModality StrEnum, SourceProfile dataclass.

Defines the single ingestion interface (D-05) that every concrete adapter implements.
The adapter is the boundary between heterogeneous EMR sources and the canonical FHIR R4B
internal representation (veridoc-fhir).

Implementations (built in 02-05):
  - NativeFhirAdapter — pass-through for sources already emitting valid FHIR R4B bundles.
  - HL7v2Adapter — parses HL7 v2.x messages via hl7apy; maps to FHIR R4B (D-12).
  - PdfExcelAdapter — rule-based extraction from structured PDFs and Excel files.
  - OcrAdapter — paper/scanned documents via OcrEngine (D-07/D-08/D-09).
  - ProprietaryAdapter — interface stub; raises NotImplementedError until D-11 contract exists.

Mirrors the KMSKeyring pattern in veridoc-crypto/kms.py exactly.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import StrEnum

__all__ = ["SourceAdapter", "SourceModality", "SourceProfile"]


class SourceModality(StrEnum):
    """Ingestion modality for a clinical site.

    Each value matches the slug used in ``urn:veridoc:source:{modality}:{site_id}``
    URNs embedded in FHIR ``Provenance.entity.what.reference`` (D-03).
    """

    NATIVE_FHIR = "native-fhir"
    HL7V2 = "hl7v2"
    PDF_EXCEL = "pdf-excel"
    OCR = "ocr"
    PROPRIETARY = "proprietary"


@dataclass(frozen=True)
class SourceProfile:
    """Per-site ingestion configuration (D-05).

    One profile per clinical site. The registry maps ``site_id`` → ``SourceProfile``
    and then maps ``modality`` → the concrete ``SourceAdapter`` subclass to invoke.

    Attributes:
        site_id: Unique clinical-site identifier (e.g. ``"site-001"``).
        modality: Ingestion modality for this site (``SourceModality`` member).
        config: Adapter-specific configuration dict (e.g. FHIR server URL,
                HL7 version string, OCR DPI setting). Content is adapter-defined.
    """

    site_id: str
    modality: SourceModality
    config: dict


class SourceAdapter(abc.ABC):
    """Single ingestion interface; N implementations per D-05.

    Every concrete adapter (NativeFhirAdapter, HL7v2Adapter, PdfExcelAdapter,
    OcrAdapter, ProprietaryAdapter) must subclass SourceAdapter and implement
    :meth:`ingest`.

    Mirrors KMSKeyring in veridoc-crypto/kms.py: ABC + abstract method + docstring
    discipline that describes each implementation's contract.
    """

    @abc.abstractmethod
    def ingest(self, payload: bytes, profile: SourceProfile) -> list:
        """Parse payload according to the site profile; return FHIR R4B resources.

        The returned list MUST include at least one resource for each success-criterion
        resource type applicable to this modality.  All PII fields MUST be replaced
        with ``pseudonym_token(...)`` output (D-14) before returning — the caller (the
        RQ worker function) does NOT re-pseudonymize.

        Args:
            payload: Raw source bytes (FHIR bundle JSON, HL7 message, PDF binary, …).
            profile: The site profile that selected this adapter.

        Returns:
            A list of ``fhir.resources.R4B`` model instances (not dicts).
        """
