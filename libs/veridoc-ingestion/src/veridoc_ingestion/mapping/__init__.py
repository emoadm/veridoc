"""HL7 v2.x → FHIR R4B mapping layer.

Currently contains:
  - hl7v2_fhir: explicit segment-level mapping (ADT_A01 → Patient/Encounter;
    ORU_R01 → Observation/DiagnosticReport). D-12: uses hl7apy, not hand-rolled.
"""

from __future__ import annotations

__all__: list[str] = []
