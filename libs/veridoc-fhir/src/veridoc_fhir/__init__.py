"""veridoc_fhir — FHIR R4B model layer and MongoDB repository (D-01/D-02/D-03).

Public API:

* FHIR R4B resource types re-exported via the ``fhir.resources.R4B`` sub-package.
  CRITICAL: top-level ``fhir.resources.*`` resolves to R5 since v7.0.0 — always
  import via ``fhir.resources.R4B.*`` (enforced by ``models.__all__``).
* :class:`FhirRepository` — async MongoDB document repository (AsyncMongoClient).
* :func:`create_provenance` — build a typed FHIR Provenance resource after each save.

Quick imports::

    from veridoc_fhir.models import Patient, Encounter, Provenance
    from veridoc_fhir.repository import FhirRepository
    from veridoc_fhir.provenance import create_provenance
    from veridoc_fhir.extensions import OCR_CONFIDENCE_URL, INGESTION_PATH_URL
"""

from __future__ import annotations

from .extensions import (
    ALCOA_LEGIBILITY_FLAG_URL,
    INGESTION_PATH_URL,
    OCR_CONFIDENCE_URL,
)
from .models import (
    AdverseEvent,
    Condition,
    DiagnosticReport,
    DocumentReference,
    Encounter,
    MedicationRequest,
    Observation,
    Patient,
    Procedure,
    Provenance,
)
from .provenance import create_provenance
from .repository import FhirRepository

__all__ = [
    # FHIR R4B resource types (D-01)
    "Patient",
    "Encounter",
    "Observation",
    "Condition",
    "MedicationRequest",
    "AdverseEvent",
    "DiagnosticReport",
    "DocumentReference",
    "Procedure",
    "Provenance",
    # MongoDB repository (D-02)
    "FhirRepository",
    # Provenance factory (D-03)
    "create_provenance",
    # Extension URL constants
    "OCR_CONFIDENCE_URL",
    "INGESTION_PATH_URL",
    "ALCOA_LEGIBILITY_FLAG_URL",
]
