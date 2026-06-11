"""NativeFhirAdapter — native FHIR R4B bundle pass-through (D-11, SC-1).

Parses a Synthea transaction Bundle (or any valid FHIR R4B bundle) into a list
of ``fhir.resources.R4B`` model instances. Patient PII (identifier values, name,
birthDate) is pseudonymized via ``veridoc_pseudonym.pseudonym_token`` before return
(D-14, SC-4).

Only the 9 canonical resource types in scope for Phase 2 are extracted from the
bundle; Claim, ExplanationOfBenefit, Immunization, and other Synthea-specific types
are excluded so the adapter output is always valid for the FHIR repository.

Security
--------
- T-02-ADP-01: Patient.identifier values replaced with pseudonymized token;
  Patient.name replaced with "PSEUDONYMIZED"; Patient.birthDate cleared.
- T-02-ADP-02: Parsing uses the fhir.resources.R4B model_validate path (Pydantic v2),
  not eval/exec or string manipulation.

Pattern analog: ``libs/veridoc-crypto/src/veridoc_crypto/kms.py`` LocalKeyring
(concrete SourceAdapter subclass with documented contract).
"""

from __future__ import annotations

import json
import uuid

from ..adapter import SourceAdapter, SourceProfile

__all__ = ["NativeFhirAdapter"]

# Resource types in scope (Phase 2 EMR-01). Synthea bundles include many others
# (Claim, ExplanationOfBenefit, Immunization, …) that we intentionally exclude.
_SCOPED_RESOURCE_TYPES = frozenset({
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
})

# Mapping from resourceType string → fhir.resources.R4B class
def _resource_class(resource_type: str):  # type: ignore[return]
    """Return the fhir.resources.R4B class for ``resource_type``.

    Raises ImportError (propagated) if the class is somehow unavailable.
    """
    from fhir.resources.R4B.patient import Patient
    from fhir.resources.R4B.encounter import Encounter
    from fhir.resources.R4B.observation import Observation
    from fhir.resources.R4B.condition import Condition
    from fhir.resources.R4B.medicationrequest import MedicationRequest
    from fhir.resources.R4B.adverseevent import AdverseEvent
    from fhir.resources.R4B.diagnosticreport import DiagnosticReport
    from fhir.resources.R4B.documentreference import DocumentReference
    from fhir.resources.R4B.procedure import Procedure
    from fhir.resources.R4B.provenance import Provenance

    _MAP = {
        "Patient": Patient,
        "Encounter": Encounter,
        "Observation": Observation,
        "Condition": Condition,
        "MedicationRequest": MedicationRequest,
        "AdverseEvent": AdverseEvent,
        "DiagnosticReport": DiagnosticReport,
        "DocumentReference": DocumentReference,
        "Procedure": Procedure,
        "Provenance": Provenance,
    }
    return _MAP.get(resource_type)


def _pseudonymize_patient(patient_dict: dict, patient_id: str, natural_id: str) -> dict:
    """Replace PII fields in a Patient dict with pseudonymized values.

    The pseudonym is deterministic: same (patient_id, natural_id) → same token
    across all adapters (SC-4, D-14). Name is replaced with "PSEUDONYMIZED";
    birthDate is cleared; identifiers replaced with the pseudo token.

    Args:
        patient_dict: Raw patient resource dict (from bundle JSON).
        patient_id: Caller-supplied opaque patient identifier (e.g. site+UUID).
        natural_id: The raw natural identifier used to derive the token (e.g. MRN).

    Returns:
        Modified patient_dict with PII replaced.
    """
    from veridoc_pseudonym import pseudonym_token

    token = pseudonym_token(patient_id, natural_id)

    # Replace Patient.id with the pseudo token
    patient_dict["id"] = token

    # Replace all identifier values with the pseudo token
    for ident in patient_dict.get("identifier", []):
        ident["value"] = token

    # Replace name with placeholder (D-14 — no raw name in FHIR output)
    patient_dict["name"] = [{"text": "PSEUDONYMIZED"}]

    # Clear birthDate (PII) — Phase 5 agents work on relative age if needed
    patient_dict.pop("birthDate", None)

    # Clear telecom, address, SSN-like fields
    patient_dict.pop("telecom", None)
    patient_dict.pop("address", None)

    return patient_dict


class NativeFhirAdapter(SourceAdapter):
    """FHIR R4B bundle pass-through adapter (D-11, SC-1).

    Parses a Synthea or native FHIR R4B transaction Bundle, extracts only the
    9 in-scope resource types, pseudonymizes Patient PII via ``pseudonym_token``,
    and returns a flat list of ``fhir.resources.R4B`` model instances.

    The ``patient_id`` used for pseudonymization is derived from the bundle Patient's
    ``id`` field (the Synthea UUID). This ensures that:
    - The same Synthea patient produces the same token across separate ingest calls.
    - The token is site-scoped via the ``profile.site_id`` prefix.
    """

    def ingest(self, payload: bytes, profile: SourceProfile) -> list:
        """Parse a FHIR R4B Bundle; return pseudonymized R4B resource list.

        Args:
            payload: Raw FHIR Bundle JSON bytes (Synthea transaction format or similar).
            profile: The site profile (site_id used as namespace prefix).

        Returns:
            List of ``fhir.resources.R4B`` model instances for the 9 in-scope types.

        Raises:
            ValueError: If the payload is not valid JSON or not a Bundle.
        """
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"NativeFhirAdapter: payload is not valid JSON — {exc}") from exc

        if data.get("resourceType") != "Bundle":
            raise ValueError(
                f"NativeFhirAdapter: expected resourceType='Bundle', "
                f"got {data.get('resourceType')!r}"
            )

        entries = data.get("entry", [])

        # First pass: find the Patient resource to extract the natural_id
        raw_patient_id: str = str(uuid.uuid4())  # fallback if no Patient
        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") == "Patient":
                raw_patient_id = resource.get("id", raw_patient_id)
                break

        # Derive a site-scoped patient_id for pseudonymization
        patient_id = f"{profile.site_id}-{raw_patient_id}"
        natural_id = raw_patient_id  # the Synthea UUID is the natural identifier

        resources: list = []

        for entry in entries:
            resource = entry.get("resource", {})
            res_type = resource.get("resourceType", "")

            if res_type not in _SCOPED_RESOURCE_TYPES:
                continue  # skip Claim, ExplanationOfBenefit, Immunization, …

            # Pseudonymize Patient PII before model validation
            if res_type == "Patient":
                resource = _pseudonymize_patient(resource, patient_id, natural_id)

            cls = _resource_class(res_type)
            if cls is None:
                continue  # safety guard

            try:
                model = cls.model_validate(resource)
                resources.append(model)
            except Exception:  # noqa: BLE001
                # Skip resources that fail R4B validation (e.g. Synthea extensions)
                continue

        return resources
