"""Concrete SourceAdapter implementations for each ingestion modality.

Currently contains:
  - ProprietaryAdapter — interface stub; raises NotImplementedError (D-11).

Plan 02-05 adds:
  - NativeFhirAdapter  — native FHIR R4B bundle pass-through.
  - HL7v2Adapter       — HL7 v2.x via hl7apy + FHIR mapping (D-12).
  - PdfExcelAdapter    — structured PDF/Excel rule-based extraction.
  - OcrAdapter         — paper/scanned via OcrEngine (D-07/D-08/D-09).
"""

from __future__ import annotations

__all__: list[str] = []
