"""Canonical VeriDoc FHIR extension URL constants.

These URNs are the authoritative identifiers for VeriDoc-specific FHIR extensions
embedded in clinical resources. They are stable and shared across the entire
``veridoc-fhir`` stack and its consumers (adapters, agents).

Usage::

    from veridoc_fhir.extensions import OCR_CONFIDENCE_URL, INGESTION_PATH_URL

Extension registry
------------------

``urn:veridoc:extension:ocr-confidence``
    Decimal (0.0–1.0) confidence score for OCR-extracted documents (D-07/D-09).
    Embedded in the FHIR Provenance resource produced by the OCR ingestion path.
    A value < 0.95 triggers an ALCOA+ legibility flag; < 0.85 triggers escalation.

``urn:veridoc:extension:ingestion-path``
    String identifying the ingestion modality that produced the FHIR resource
    (e.g. ``"native-fhir"``, ``"hl7v2"``, ``"ocr"``, ``"pdf-excel"``).
    Always present on every Provenance resource produced by this stack.

``urn:veridoc:extension:alcoa-legibility-flag``
    String carrying an ALCOA+ legibility flag code (``"legibility-flag"`` or
    ``"legibility-escalate"``). Multiple instances may appear on a single
    DocumentReference when the confidence crosses multiple thresholds.
"""

from __future__ import annotations

#: OCR confidence score (Decimal 0.0–1.0). Used in Provenance + DocumentReference.
OCR_CONFIDENCE_URL: str = "urn:veridoc:extension:ocr-confidence"

#: Ingestion path identifier (String). Always present on FHIR Provenance resources.
INGESTION_PATH_URL: str = "urn:veridoc:extension:ingestion-path"

#: ALCOA+ legibility flag (String: ``"legibility-flag"`` | ``"legibility-escalate"``).
ALCOA_LEGIBILITY_FLAG_URL: str = "urn:veridoc:extension:alcoa-legibility-flag"

__all__ = [
    "OCR_CONFIDENCE_URL",
    "INGESTION_PATH_URL",
    "ALCOA_LEGIBILITY_FLAG_URL",
]
