"""veridoc_ingestion — EMR ingestion adapters and queue helpers (D-04–D-14).

Public API (populated by later plans):

* :class:`SourceAdapter` — ABC for all ingestion adapters (native FHIR, HL7 v2.x,
  PDF/Excel, OCR, proprietary).
* :class:`SourceProfile` — per-site source configuration dataclass.
* :class:`SourceModality` — StrEnum of the five ingestion modalities (D-11).
* :class:`OcrEngine` — portable OCR abstraction (Tesseract default; D-07/D-08).
* :class:`BlobStore` — S3-compatible blob storage abstraction (MinIO/S3; D-10).
* ``ingest_job`` — RQ worker function with JSONSerializer-only arguments (D-06).

This module is intentionally thin at Wave 0; it is populated by plans 02-03 through 02-06.
"""

from __future__ import annotations

__all__: list[str] = []
