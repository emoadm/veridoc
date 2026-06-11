"""HL7v2Adapter — HL7 v2.x messages → FHIR R4B resources (D-11, D-12, SC-2a).

Delegates all segment-level parsing to the explicit mapping layer
(:mod:`veridoc_ingestion.mapping.hl7v2_fhir`) which uses ``hl7apy.parser.parse_message``
for structured field access.  This adapter is responsible for:

1. Detecting the HL7 message type from MSH-9.
2. Calling the appropriate mapping function (map_adt_a01_to_fhir / map_oru_r01_to_fhir).
3. Deriving the ``patient_id`` for pseudonymization from PID.3 (CX_1 stripped of
   assigning authority — open question #3).
4. Applying ``pseudonym_token(patient_id, natural_id)`` to derive the patient-scoped
   token (D-14, SC-4).

Security
--------
- T-02-ADP-01: patient_id is derived via pseudonym_token; no raw MRN appears in output.
- T-02-ADP-02: hl7apy structured parsing; unknown message types raise ValueError.
- Input bytes are decoded as UTF-8 (strict); malformed byte sequences raise ValueError.

Pattern analog: ``libs/veridoc-crypto/src/veridoc_crypto/kms.py`` LocalKeyring
(concrete SourceAdapter with documented contract, delegates crypto to the key module).
"""

from __future__ import annotations

from ..adapter import SourceAdapter, SourceProfile
from ..mapping import hl7v2_fhir

__all__ = ["HL7v2Adapter"]


def _extract_natural_id(hl7_msg_str: str) -> str:
    """Extract the natural patient ID from PID.3 CX_1 (open question #3).

    Uses hl7apy to access the CX_1 sub-component (raw ID without assigning authority).
    Falls back to the full PID.3 value if sub-component access fails.

    Args:
        hl7_msg_str: Normalized HL7 ER7 string (CR-separated).

    Returns:
        The raw patient identifier string (CX_1).
    """
    from hl7apy.parser import parse_message

    msg = parse_message(hl7_msg_str, find_groups=False)
    pid = next((c for c in msg.children if c.name == "PID"), None)
    if pid is None:
        return "UNKNOWN"

    try:
        # PID.3 is a CX-encoded identifier: ID^^^Authority^type
        # CX_1 is the raw ID component (open question #3: use CX_1, not the full CX value)
        cx1 = pid.pid_3.cx_1.value
        return cx1 if cx1 else pid.pid_3.value
    except Exception:  # noqa: BLE001
        return pid.pid_3.value or "UNKNOWN"


class HL7v2Adapter(SourceAdapter):
    """HL7 v2.x → FHIR R4B adapter using hl7apy + explicit mapping layer (D-12).

    Supported message types:
      - ADT_A01 (admission) → [Patient, Encounter]
      - ORU_R01 (lab results) → [Observation(+), DiagnosticReport]

    The pseudonymized patient_id is derived from PID.3 CX_1 and ``profile.site_id``.
    This ensures cross-source matching: the same MRN at the same site always produces
    the same token (SC-4, Phase-5 matching precondition).
    """

    def ingest(self, payload: bytes, profile: SourceProfile) -> list:
        """Parse HL7 v2.x payload; return pseudonymized R4B resource list.

        Args:
            payload: Raw HL7 v2.x ER7-encoded bytes (UTF-8).
            profile: Site profile (site_id used as namespace prefix for patient_id).

        Returns:
            List of ``fhir.resources.R4B`` model instances.

        Raises:
            ValueError: On decode failure, unknown message type, or missing PID.
        """
        from hl7apy.parser import parse_message
        from veridoc_pseudonym import patient_pseudonym

        try:
            hl7_str = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"HL7v2Adapter: payload is not valid UTF-8 — {exc}") from exc

        # Normalize LF → CR (hl7apy requires CR as segment separator)
        normalized = hl7_str.replace("\n", "\r").strip()

        # Detect message type from MSH-9
        msg = parse_message(normalized, find_groups=False)
        msh = next((c for c in msg.children if c.name == "MSH"), None)
        if msh is None:
            raise ValueError("HL7v2Adapter: MSH segment not found in message")

        msg_type = msh.msh_9.value  # e.g. "ADT^A01^ADT_A01"
        msg_struct = msh.msh_9.msg_3.value if msh.msh_9.msg_3.value else ""
        # Fallback: derive from type + trigger
        if not msg_struct:
            msg_code = msh.msh_9.msg_1.value
            trigger = msh.msh_9.msg_2.value
            msg_struct = f"{msg_code}_{trigger}"

        # Derive pseudonymized patient_id from PID.3 CX_1 using the SINGLE canonical
        # per-patient key-namespace shared by all adapters (CR-05): site_id+natural_id.
        natural_id = _extract_natural_id(normalized)
        patient_id = patient_pseudonym(profile.site_id, natural_id)

        # Authoritative dispatch on the parsed (message code, trigger event) tuple
        # from MSH-9 — NOT a substring test on the raw value (WR-04: substring
        # matching is order-sensitive and can match unintended composite types).
        msg_code = msh.msh_9.msg_1.value or ""
        trigger = msh.msh_9.msg_2.value or ""
        dispatch = (msg_code, trigger)

        # Dispatch to the explicit mapping layer (D-12). site_id is threaded
        # through so every emitted resource carries meta.source (CR-06 / WR-07).
        if dispatch == ("ADT", "A01") or msg_struct == "ADT_A01":
            return hl7v2_fhir.map_adt_a01_to_fhir(normalized, patient_id, profile.site_id)
        elif dispatch == ("ORU", "R01") or msg_struct == "ORU_R01":
            return hl7v2_fhir.map_oru_r01_to_fhir(normalized, patient_id, profile.site_id)
        else:
            raise ValueError(
                f"HL7v2Adapter: unsupported message type {msg_type!r} "
                f"(supported: ADT_A01, ORU_R01)"
            )
