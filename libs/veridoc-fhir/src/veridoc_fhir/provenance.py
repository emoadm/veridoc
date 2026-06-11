"""FHIR Provenance factory (D-03).

Provides :func:`create_provenance`, a factory that constructs a spec-native FHIR R4B
Provenance resource after each resource save. The Provenance carries:

- ``target``: a reference to the saved resource (pseudonymized reference).
- ``recorded``: the ingestion instant (always timezone-aware — Pitfall 9).
- ``meta.source``: the source system URN (mirrors resource.meta.source for provenance).
- ``agent``: the ingestion service device reference.
- ``entity``: the originating source system reference + role="source".
- ``extension[ingestion-path]``: always present; identifies the ingestion modality.
- ``extension[ocr-confidence]``: present only when ``ocr_confidence`` is not None.

Security notes
--------------
- ``entity.what.reference`` carries the pseudonymized reference (source URN or
  pseudonymized patient ref), NEVER a natural_id (T-02-FHIR-03).
- ``recorded`` uses ``datetime.now(timezone.utc).isoformat()`` to produce a
  timezone-aware ISO 8601 instant. Naive ``datetime.now()`` raises a Pydantic
  ValidationError in fhir.resources.R4B (Pitfall 9).

Analogue: ``services/reference-service/src/reference_service/api/subjects.py``
(provenance metadata embedded in audit event after business operation).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fhir.resources.R4B.provenance import Provenance

from .extensions import INGESTION_PATH_URL, OCR_CONFIDENCE_URL

__all__ = ["create_provenance"]


def create_provenance(
    target_ref: str,
    source: str,
    ingestion_path: str,
    actor_ref: str,
    ocr_confidence: float | None = None,
) -> Provenance:
    """Build a FHIR R4B Provenance after an ingest save.

    Parameters
    ----------
    target_ref:
        Pseudonymized reference to the primary saved resource
        (e.g. ``"Patient/p-pseudo-abc123"``).
    source:
        Source system URN identifying where the data originated
        (e.g. ``"urn:veridoc:source:native-fhir:site-001"``). Set as both
        ``entity.what.reference`` and ``meta.source`` on this Provenance.
    ingestion_path:
        The ingestion modality string (e.g. ``"native-fhir"``, ``"hl7v2"``,
        ``"ocr"``). Always emitted as the ``ingestion-path`` extension.
    actor_ref:
        Reference to the ingestion actor (e.g. ``"Device/ingestion-service"``).
    ocr_confidence:
        Optional float in [0.0, 1.0]. When not ``None`` (including ``0.0``),
        an ``ocr-confidence`` extension is added. Absent for non-OCR paths.

    Returns
    -------
    Provenance
        A fully-validated ``fhir.resources.R4B.provenance.Provenance`` instance.
    """
    # Build extensions list: ingestion-path always first; ocr-confidence conditional.
    extensions: list[dict] = []

    # ocr-confidence extension: present iff ocr_confidence is not None (0.0 is valid).
    if ocr_confidence is not None:
        extensions.append({
            "url": OCR_CONFIDENCE_URL,
            "valueDecimal": ocr_confidence,
        })

    # ingestion-path extension: always present.
    extensions.append({
        "url": INGESTION_PATH_URL,
        "valueString": ingestion_path,
    })

    # recorded: MUST be timezone-aware (Pitfall 9 — naive datetime raises ValidationError).
    recorded = datetime.now(timezone.utc).isoformat()

    return Provenance.model_validate({
        "resourceType": "Provenance",
        "meta": {
            "source": source,
        },
        "target": [{"reference": target_ref}],
        "recorded": recorded,
        "agent": [{"who": {"reference": actor_ref}}],
        "entity": [
            {
                "role": "source",
                "what": {"reference": source},
            }
        ],
        "extension": extensions,
    })
