"""FHIR R4B resource type re-exports (D-01).

Provides a thin facade over the ``fhir.resources.R4B`` sub-package, re-exporting
the 9 canonical clinical resource types + Provenance via ``__all__``.

**CRITICAL:** From ``fhir.resources`` v7.0.0 onwards the top-level namespace
(``fhir.resources.patient``) resolves to FHIR **R5**, not R4. Always import via the
``fhir.resources.R4B.*`` sub-package path. This module enforces that discipline for
the entire ``veridoc-fhir`` stack by:

1. Importing exclusively from ``fhir.resources.R4B.*``.
2. Gating the public API via ``__all__`` so any ``from veridoc_fhir.models import *``
   can never accidentally pull in an R5 class.

The 9 resource types in scope (EMR-01):
- Patient
- Encounter
- Observation
- Condition
- MedicationRequest
- AdverseEvent
- DiagnosticReport
- DocumentReference
- Procedure
- Provenance (FHIR spec-native provenance, D-03)
"""

from __future__ import annotations

# CRITICAL: always R4B sub-package — top-level now resolves to R5 (since v7.0.0)
from fhir.resources.R4B.adverseevent import AdverseEvent
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.diagnosticreport import DiagnosticReport
from fhir.resources.R4B.documentreference import DocumentReference
from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.medicationrequest import MedicationRequest
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.procedure import Procedure
from fhir.resources.R4B.provenance import Provenance

__all__ = [
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
]
