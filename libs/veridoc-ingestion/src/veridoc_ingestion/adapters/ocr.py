"""OcrAdapter — scanned documents → FHIR DocumentReference + OCR confidence (D-11, SC-3, D-09).

Runs :class:`~veridoc_ingestion.ocr_engine.OcrEngine` on image bytes, stores the
original to :class:`~veridoc_ingestion.blob_store.BlobStore` under a UUID+site_id key,
and builds a FHIR R4B :class:`~fhir.resources.R4B.documentreference.DocumentReference`
carrying:

- ``docStatus = "preliminary"`` (pending ALCOA+ legibility review in Phase 5)
- ``content.attachment.url`` = blob URI (ALCOA+ Original principle: original retained)
- Extension ``urn:veridoc:extension:ocr-confidence`` = OcrResult.document_confidence
- Extension ``urn:veridoc:extension:alcoa-legibility-flag`` = ``"legibility-flag"``
  when ``document_confidence < 0.95`` (ALCOA-01 legibility flag)
- Extension ``urn:veridoc:extension:alcoa-legibility-flag`` = ``"legibility-escalate"``
  when ``document_confidence < 0.85`` (must escalate to human review)

The subject reference is pseudonymized via ``pseudonym_token`` (D-14).

**OCR confidence + ALCOA flags are ALWAYS derived server-side from OcrEngine output**
(not from request input) — T-02-ADP-04 mitigated.

Dependencies (injected; default to Tesseract + S3):
- ``ocr_engine``: :class:`~veridoc_ingestion.ocr_engine.TesseractEngine` (default)
- ``blob_store``: :class:`~veridoc_ingestion.blob_store.S3BlobStore` (default,
  requires MinIO or S3 credentials in the environment)

Pattern analog: :class:`~veridoc_ingestion.adapters.native_fhir.NativeFhirAdapter`
(same return type; same pseudonymization discipline) + RESEARCH.md Pattern 9.

Usage::

    from veridoc_ingestion.adapters.ocr import OcrAdapter
    from veridoc_ingestion.ocr_engine import TesseractEngine
    from veridoc_ingestion.blob_store import S3BlobStore

    adapter = OcrAdapter(
        ocr_engine=TesseractEngine(),
        blob_store=S3BlobStore(bucket="veridoc-docs", endpoint_url="http://minio:9000"),
    )
    resources = adapter.ingest(image_bytes, profile)  # → [DocumentReference]
"""

from __future__ import annotations

import uuid

from ..adapter import SourceAdapter, SourceProfile
from ..blob_store import BlobStore
from ..ocr_engine import OcrEngine

__all__ = ["OcrAdapter"]


def _build_document_reference(
    blob_uri: str,
    patient_ref: str,
    ocr_confidence: float,
    mime_type: str,
    site_id: str,
) -> object:
    """Build a FHIR R4B DocumentReference per RESEARCH.md Pattern 9 (D-09).

    Args:
        blob_uri: URI of the stored original (e.g. ``"s3://bucket/site-001/scan.png"``).
        patient_ref: Pseudonymized patient reference (e.g. ``"Patient/pseudo-abc123"``).
        ocr_confidence: OcrResult.document_confidence (0.0–1.0). Derived server-side.
        mime_type: Content type of the image (e.g. ``"image/png"``).
        site_id: Clinical site identifier.

    Returns:
        A fully-validated ``fhir.resources.R4B.documentreference.DocumentReference``.
    """
    from fhir.resources.R4B.documentreference import DocumentReference
    from veridoc_fhir.extensions import OCR_CONFIDENCE_URL, ALCOA_LEGIBILITY_FLAG_URL

    # ALCOA+ legibility flags (derived server-side from OcrEngine — T-02-ADP-04)
    extensions: list[dict] = [
        {
            "url": OCR_CONFIDENCE_URL,
            "valueDecimal": round(ocr_confidence, 6),
        }
    ]
    if ocr_confidence < 0.95:
        extensions.append({
            "url": ALCOA_LEGIBILITY_FLAG_URL,
            "valueString": "legibility-flag",
        })
    if ocr_confidence < 0.85:
        extensions.append({
            "url": ALCOA_LEGIBILITY_FLAG_URL,
            "valueString": "legibility-escalate",
        })

    return DocumentReference.model_validate({
        "resourceType": "DocumentReference",
        "id": str(uuid.uuid4()),
        "meta": {
            "source": f"urn:veridoc:source:ocr:{site_id}",
        },
        "status": "current",
        "docStatus": "preliminary",      # pending ALCOA+ legibility review (open question #2)
        "subject": {"reference": patient_ref},
        "content": [
            {
                "attachment": {
                    "contentType": mime_type,
                    "url": blob_uri,     # points to retained original (ALCOA+ Original)
                }
            }
        ],
        "extension": extensions,
    })


class OcrAdapter(SourceAdapter):
    """OCR-path adapter: image → DocumentReference + blob retention (D-11, SC-3, D-09).

    Injects an :class:`~veridoc_ingestion.ocr_engine.OcrEngine` and a
    :class:`~veridoc_ingestion.blob_store.BlobStore`. Both default to
    :class:`~veridoc_ingestion.ocr_engine.TesseractEngine` and
    :class:`~veridoc_ingestion.blob_store.S3BlobStore` respectively, but any
    implementation conforming to those ABCs can be injected (e.g. stub in tests).

    The ``patient_id`` for pseudonymization is taken from ``profile.site_id`` +
    a random UUID (no patient identifier is available from raw image bytes).
    Callers may override by subclassing or by injecting a pre-pseudonymized
    patient_id via ``profile.config["patient_id"]``.
    """

    def __init__(
        self,
        ocr_engine: OcrEngine | None = None,
        blob_store: BlobStore | None = None,
    ) -> None:
        """Initialize the OCR adapter.

        Args:
            ocr_engine: OCR engine to use. Defaults to :class:`TesseractEngine`.
            blob_store: Blob store to use. Defaults to :class:`S3BlobStore`
                        (requires env vars ``VERIDOC_BLOB_BUCKET``,
                        ``VERIDOC_BLOB_ENDPOINT_URL``, etc.).
        """
        if ocr_engine is None:
            from ..ocr_engine import TesseractEngine
            ocr_engine = TesseractEngine()
        self._ocr_engine = ocr_engine

        if blob_store is None:
            import os
            from ..blob_store import S3BlobStore
            blob_store = S3BlobStore(
                bucket=os.environ.get("VERIDOC_BLOB_BUCKET", "veridoc-docs"),
                endpoint_url=os.environ.get("VERIDOC_BLOB_ENDPOINT_URL") or None,
                access_key=os.environ.get("VERIDOC_BLOB_ACCESS_KEY", ""),
                secret_key=os.environ.get("VERIDOC_BLOB_SECRET_KEY", ""),
            )
        self._blob_store = blob_store

    def ingest(self, payload: bytes, profile: SourceProfile) -> list:
        """Run OCR on image bytes; store original; return [DocumentReference].

        Args:
            payload: Raw image bytes (PNG, TIFF, JPEG, …).
            profile: Site profile.  ``profile.config.get("patient_id")`` overrides
                     the auto-generated pseudonymized patient reference.
                     ``profile.config.get("content_type")`` sets the MIME type
                     (defaults to ``"image/png"``).

        Returns:
            List containing one :class:`DocumentReference` (possibly more in future).

        Raises:
            Any exception from the OCR engine or blob store propagates to the caller.
        """
        from veridoc_pseudonym import patient_pseudonym

        # Derive pseudonymized patient_id using the SINGLE canonical per-patient
        # key-namespace shared by all adapters (CR-05): site_id + natural_id.
        # If profile.config provides a patient_id, use it; otherwise generate one.
        raw_patient_id = profile.config.get("patient_id", str(uuid.uuid4()))
        patient_id = patient_pseudonym(profile.site_id, raw_patient_id)
        patient_ref = f"Patient/{patient_id}"

        # Content type (default: image/png)
        content_type = profile.config.get("content_type", "image/png")

        # Determine file extension from content type
        _ext_map = {
            "image/png": "png",
            "image/tiff": "tiff",
            "image/jpeg": "jpg",
            "image/jpg": "jpg",
        }
        ext = _ext_map.get(content_type.lower(), "bin")

        # Store original to blob store (ALCOA+ Original principle — D-10)
        blob_key = f"{profile.site_id}/{uuid.uuid4()}.{ext}"
        blob_uri = self._blob_store.put(blob_key, payload, content_type)

        # Run OCR and compute confidence + ALCOA flags (server-side only — T-02-ADP-04)
        ocr_result = self._ocr_engine.extract(payload, content_type)

        # Build DocumentReference with ocr-confidence + legibility flags
        doc_ref = _build_document_reference(
            blob_uri=blob_uri,
            patient_ref=patient_ref,
            ocr_confidence=ocr_result.document_confidence,
            mime_type=content_type,
            site_id=profile.site_id,
        )

        return [doc_ref]
