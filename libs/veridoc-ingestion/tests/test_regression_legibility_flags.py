"""Regression test for IN-01 — both ALCOA legibility-flag instances coexist.

IN-01 noted that ``ALCOA_LEGIBILITY_FLAG_URL`` has a single consumer (the OCR
adapter) and that, below confidence 0.85, TWO extension instances with the same
URL must coexist on one DocumentReference (``legibility-flag`` AND
``legibility-escalate``). This asserts that multi-instance data model directly.
"""

from __future__ import annotations


def _doc_below_085():
    from veridoc_ingestion.adapters.ocr import OcrAdapter
    from veridoc_ingestion.adapter import SourceModality, SourceProfile
    from veridoc_ingestion.ocr_engine import OcrEngine, OcrResult
    from veridoc_ingestion.blob_store import BlobStore

    class _StubEngine(OcrEngine):
        def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
            return OcrResult(
                text="x",
                document_confidence=0.80,
                word_confidences=[0.80],
                flagged=True,
                escalated=True,
            )

    class _StubBlob(BlobStore):
        def put(self, key: str, data: bytes, content_type: str) -> str:
            return f"s3://stub/{key}"

        def get(self, key: str) -> bytes:  # pragma: no cover
            return b""

    profile = SourceProfile(site_id="site-001", modality=SourceModality.OCR, config={})
    adapter = OcrAdapter(ocr_engine=_StubEngine(), blob_store=_StubBlob())
    resources = adapter.ingest(b"fake-image", profile)
    return next(r for r in resources if r.get_resource_type() == "DocumentReference")


def test_two_legibility_flag_instances_coexist():
    """Below 0.85, the DocumentReference carries BOTH legibility flag instances (IN-01)."""
    from veridoc_fhir.extensions import ALCOA_LEGIBILITY_FLAG_URL

    doc = _doc_below_085()
    flags = [e for e in (doc.extension or []) if e.url == ALCOA_LEGIBILITY_FLAG_URL]
    values = {e.valueString for e in flags}

    assert len(flags) == 2, (
        f"Expected two {ALCOA_LEGIBILITY_FLAG_URL} instances, got {len(flags)}"
    )
    assert values == {"legibility-flag", "legibility-escalate"}, (
        f"Both flag values must coexist, got {values}"
    )
