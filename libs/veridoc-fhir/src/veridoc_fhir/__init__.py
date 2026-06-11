"""veridoc_fhir — FHIR R4B model layer and MongoDB repository (D-01/D-02/D-03).

Public API (populated by later plans):

* FHIR R4B resource types re-exported via the ``fhir.resources.R4B`` sub-package
  (CRITICAL: top-level ``fhir.resources.*`` resolves to R5 since v7.0.0 — always
  import via ``fhir.resources.R4B.*``).
* :class:`FhirRepository` — async MongoDB document repository (AsyncMongoClient).
* :func:`create_provenance` — build a typed FHIR Provenance resource after each save.

This module is intentionally thin at Wave 0; it is populated by plans 02-02 through 02-04.
"""

from __future__ import annotations

__all__: list[str] = []
