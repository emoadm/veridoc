"""Explicit HL7 v2.x segment → FHIR R4B mapping layer (D-12).

This module provides the explicit, library-based HL7 v2 → FHIR R4B mapping.  It uses
``hl7apy.parser.parse_message`` for structured field access — NOT a hand-rolled ER7
parser (D-12: vetted hl7apy library + explicit mapping layer per RESEARCH.md Pattern 8).

Supported message types
-----------------------
ADT_A01 (admission):
  PID → Patient  (pseudonymized name/DOB/identifiers — D-14)
  PV1 → Encounter  (class: E→EMER, I→IMP, O→AMB, P→PRENC — official HL7 ConceptMap)
  EVN → Provenance metadata (recorded datetime)

ORU_R01 (lab results):
  PID → Patient  (pseudonymized)
  OBX(+) → Observation  (LOINC from OBX-3, value from OBX-5, units from OBX-6)
  OBR → DiagnosticReport  (LOINC from OBR-4 code)

Open question #3 (PID.3.1 natural_id):
  PID.3 (CX-encoded patient identifier) has the form ``ID^^^Authority^type``.
  We use PID.3 CX_1 (the raw ID component) as ``natural_id`` for ``pseudonym_token``,
  stripping the assigning authority. This matches RESEARCH.md open question #3 recommendation:
  "just the ID portion" — the assigning authority is site metadata, not patient identity.

Security notes
--------------
- All HL7 fields are accessed via hl7apy structured objects, never via substring/regex
  on raw ER7 strings (T-02-ADP-02: no parser abuse via malformed HL7).
- Unknown message types raise ValueError clearly instead of silently returning empty.
- PII fields (name, DOB, identifiers) are pseudonymized by the caller (HL7v2Adapter)
  before the returned resources are passed to any downstream layer.

Usage::

    resources = map_adt_a01_to_fhir(hl7_msg_str, patient_id="site-001-patient")
    resources = map_oru_r01_to_fhir(hl7_msg_str, patient_id="site-001-patient")
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

__all__ = ["map_adt_a01_to_fhir", "map_oru_r01_to_fhir"]

# PV1.2 class code mapping (official HL7 ConceptMap, hl7.org/fhir/uv/v2mappings)
_PV1_CLASS_MAP: dict[str, str] = {
    "E": "EMER",   # Emergency
    "I": "IMP",    # Inpatient
    "O": "AMB",    # Outpatient → Ambulatory
    "P": "PRENC",  # Pre-admission
}


def _parse_hl7_datetime(value: str) -> str:
    """Convert HL7 DTM (YYYYMMDDHHmmSS) to ISO 8601 UTC string.

    Args:
        value: HL7 datetime string (YYYYMMDDHHMMSS or subset).

    Returns:
        ISO 8601 string, timezone-aware (UTC assumed for HL7 local times).
    """
    if not value:
        return datetime.now(timezone.utc).isoformat()
    formats = ["%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(value[:len(fmt.replace("%", "XX"))], fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return datetime.now(timezone.utc).isoformat()


def _parse_hl7_date(value: str) -> str | None:
    """Convert HL7 date (YYYYMMDD) to ISO date string (YYYY-MM-DD).

    Args:
        value: HL7 date string (YYYYMMDD).

    Returns:
        ISO date string or None if value is empty/unparseable.
    """
    if not value or len(value) < 8:
        return None
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def _hl7_source_urn(site_id: str) -> str:
    """Canonical HL7v2 source URN for a site (CR-06 / WR-07).

    Used as ``meta.source`` on EVERY resource the HL7 mapping emits so the
    (resourceType, meta.source) index and source-attribution queries resolve, and
    ALCOA "Attributable" holds for the whole HL7 path — not just Patient.
    """
    return f"urn:veridoc:source:hl7v2:{site_id}"


def map_adt_a01_to_fhir(hl7_msg_str: str, patient_id: str, site_id: str) -> list:
    """Map an ADT_A01 HL7 v2.x message to FHIR R4B [Patient, Encounter].

    Uses hl7apy structured field access (D-12). PID.3 CX_1 is used as the
    ``natural_id`` for pseudonymization (open question #3). The ``patient_id``
    arg becomes the pseudonymized Patient.id and Encounter.subject.reference.

    Args:
        hl7_msg_str: Raw HL7 v2.x ER7-encoded string (newlines OR carriage returns).
        patient_id: Pseudonymized patient identifier (from caller; already derived
                    via pseudonym_token before this function is called).
        site_id: The real clinical-site identifier; used to stamp
                 ``meta.source = urn:veridoc:source:hl7v2:{site_id}`` on every
                 emitted resource (CR-06 / WR-07).

    Returns:
        List of fhir.resources.R4B model instances: [Patient, Encounter].
    """
    from hl7apy.parser import parse_message
    from fhir.resources.R4B.patient import Patient
    from fhir.resources.R4B.encounter import Encounter

    source_urn = _hl7_source_urn(site_id)

    # hl7apy requires CR (\r) as segment separator; normalize LF → CR
    normalized = hl7_msg_str.replace("\n", "\r").strip()
    msg = parse_message(normalized, find_groups=False)

    # --- PID segment → Patient -------------------------------------------
    pid = next((c for c in msg.children if c.name == "PID"), None)

    # Patient.identifier (pseudonymized — raw MRN replaced by patient_id token)
    patient = Patient.model_validate({
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {
            "source": source_urn,  # CR-06: real site_id, not the literal "site"
        },
        "identifier": [
            {
                "system": "urn:veridoc:pseudonym",
                "value": patient_id,
            }
        ],
        # name, birthDate, gender pseudonymized: not included in output (D-14)
        "active": True,
    })

    # --- PV1 segment → Encounter ------------------------------------------
    pv1 = next((c for c in msg.children if c.name == "PV1"), None)
    evn = next((c for c in msg.children if c.name == "EVN"), None)

    # PV1.2 → encounter class (E/I/O/P → EMER/IMP/AMB/PRENC)
    raw_class = pv1.pv1_2.value if pv1 else ""
    enc_class_code = _PV1_CLASS_MAP.get(raw_class.strip(), "AMB")

    # EVN.2 → admission datetime
    admission_ts = evn.evn_2.value if evn else ""
    admission_dt = _parse_hl7_datetime(admission_ts)

    encounter = Encounter.model_validate({
        "resourceType": "Encounter",
        "id": str(uuid.uuid4()),
        "meta": {"source": source_urn},  # WR-07: attribution on Encounter too
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": enc_class_code,
            "display": enc_class_code,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {"start": admission_dt},
    })

    return [patient, encounter]


def map_oru_r01_to_fhir(hl7_msg_str: str, patient_id: str, site_id: str) -> list:
    """Map an ORU_R01 HL7 v2.x message to FHIR R4B [Observation(+), DiagnosticReport].

    Uses hl7apy structured field access (D-12).  OBX-3 → Observation.code (LOINC);
    OBX-5 → Observation.valueQuantity; OBX-6 → units.  OBR-4 → DiagnosticReport.code.

    Args:
        hl7_msg_str: Raw HL7 v2.x ER7-encoded string.
        patient_id: Pseudonymized patient identifier (from caller).
        site_id: The real clinical-site identifier; used to stamp
                 ``meta.source = urn:veridoc:source:hl7v2:{site_id}`` on every
                 emitted resource (WR-07).

    Returns:
        List of fhir.resources.R4B model instances: [Observation, ..., DiagnosticReport].
    """
    from hl7apy.parser import parse_message
    from fhir.resources.R4B.observation import Observation
    from fhir.resources.R4B.diagnosticreport import DiagnosticReport

    source_urn = _hl7_source_urn(site_id)

    normalized = hl7_msg_str.replace("\n", "\r").strip()
    msg = parse_message(normalized, find_groups=False)

    # --- OBR segment → DiagnosticReport code ---
    obr = next((c for c in msg.children if c.name == "OBR"), None)
    dr_code_raw = obr.obr_4.value if obr else ""
    dr_parts = dr_code_raw.split("^") if dr_code_raw else []
    dr_loinc_code = dr_parts[0] if dr_parts else ""
    dr_loinc_display = dr_parts[1] if len(dr_parts) > 1 else dr_loinc_code

    # --- OBX segments → Observations --------------------------------------
    obx_list = [c for c in msg.children if c.name == "OBX"]
    observations: list = []
    obs_refs: list[dict] = []

    for obx in obx_list:
        # OBX-3: LOINC code^display^system  (CE-encoded)
        obx3_raw = obx.obx_3.value if obx.obx_3 else ""
        obx3_parts = obx3_raw.split("^") if obx3_raw else []
        loinc_code = obx3_parts[0] if obx3_parts else ""
        loinc_display = obx3_parts[1] if len(obx3_parts) > 1 else loinc_code
        loinc_system = obx3_parts[2] if len(obx3_parts) > 2 else "LN"
        # LN = LOINC; normalize to full URI
        coding_system = (
            "http://loinc.org" if loinc_system in ("LN", "LNC", "LOINC") else loinc_system
        )

        # OBX-5: value (NM type → numeric)
        obx5_raw = obx.obx_5.value if obx.obx_5 else ""

        # OBX-6: units (CE-encoded: unit^display^system)
        obx6_raw = obx.obx_6.value if obx.obx_6 else ""
        obx6_parts = obx6_raw.split("^") if obx6_raw else []
        unit_code = obx6_parts[0] if obx6_parts else ""
        unit_system = obx6_parts[2] if len(obx6_parts) > 2 else ""
        unit_system_uri = (
            "http://unitsofmeasure.org" if unit_system in ("UCUM",) else unit_system
        )

        obs_id = str(uuid.uuid4())

        # Build valueQuantity if numeric
        value_quantity = None
        try:
            numeric_val = float(obx5_raw)
            value_quantity = {
                "value": numeric_val,
                "unit": unit_code,
                "system": unit_system_uri if unit_system_uri else "http://unitsofmeasure.org",
                "code": unit_code,
            }
        except (ValueError, TypeError):
            pass  # non-numeric value; skip valueQuantity

        obs_dict: dict = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": {"source": source_urn},  # WR-07: attribution on each Observation
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": coding_system,
                        "code": loinc_code,
                        "display": loinc_display,
                    }
                ],
                "text": loinc_display,
            },
            "subject": {"reference": f"Patient/{patient_id}"},
        }
        if value_quantity:
            obs_dict["valueQuantity"] = value_quantity

        obs = Observation.model_validate(obs_dict)
        observations.append(obs)
        obs_refs.append({"reference": f"Observation/{obs_id}"})

    # --- DiagnosticReport ------------------------------------------------
    dr = DiagnosticReport.model_validate({
        "resourceType": "DiagnosticReport",
        "id": str(uuid.uuid4()),
        "meta": {"source": source_urn},  # WR-07: attribution on DiagnosticReport
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": dr_loinc_code,
                    "display": dr_loinc_display,
                }
            ],
            "text": dr_loinc_display,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "result": obs_refs,
    })

    return observations + [dr]
