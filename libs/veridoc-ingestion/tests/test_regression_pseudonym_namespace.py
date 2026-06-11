"""Regression test for CR-05 — one canonical pseudonym key-namespace for all adapters.

CR-05: ``pseudonym_token(patient_id, natural_id)`` derives the *per-patient* crypto
key from its FIRST argument. For per-patient crypto-shredding (D-14) and cross-source
matching (SC-4) to both hold, every adapter must derive that first argument
identically as ``patient_key_namespace(site_id, natural_id) == f"{site}-{natural}"``.

Previously native_fhir used the per-patient namespace while hl7v2 / pdf_excel / ocr
used the per-SITE namespace (``site_id`` alone), so the same physical patient got
unrelated tokens across modalities. These in-process tests (no Docker) assert that:

1. All four adapters import and route through the single canonical helper.
2. Given the SAME (site, natural_id), the canonical token is identical — and the
   OCR adapter (drivable with a controlled natural_id) emits exactly that token.
"""

from __future__ import annotations

import inspect

import pytest


SITE = "site-001"
NATURAL_ID = "PT-CROSS-SOURCE-42"


def _expected_token() -> str:
    from veridoc_pseudonym import patient_pseudonym

    return patient_pseudonym(SITE, NATURAL_ID)


def test_canonical_namespace_is_site_dash_natural():
    """The canonical namespace is exactly f'{site}-{natural_id}' (the per-patient key)."""
    from veridoc_pseudonym import patient_key_namespace, patient_pseudonym, pseudonym_token

    assert patient_key_namespace(SITE, NATURAL_ID) == f"{SITE}-{NATURAL_ID}"
    # patient_pseudonym must equal pseudonym_token over the canonical namespace.
    assert patient_pseudonym(SITE, NATURAL_ID) == pseudonym_token(
        f"{SITE}-{NATURAL_ID}", NATURAL_ID
    )


@pytest.mark.parametrize(
    "module_path",
    [
        "veridoc_ingestion.adapters.native_fhir",
        "veridoc_ingestion.adapters.hl7v2",
        "veridoc_ingestion.adapters.pdf_excel",
        "veridoc_ingestion.adapters.ocr",
    ],
)
def test_all_adapters_use_canonical_helper(module_path):
    """Every adapter routes pseudonymization through patient_pseudonym (CR-05).

    Guards against an adapter regressing to pseudonym_token(site_id, ...) (per-site
    namespace) or any bespoke scheme that would break cross-source matching.
    """
    import importlib

    mod = importlib.import_module(module_path)
    src = inspect.getsource(mod)
    assert "patient_pseudonym" in src, (
        f"{module_path} must derive patient tokens via the canonical "
        f"patient_pseudonym(site_id, natural_id) helper (CR-05)"
    )
    # The per-site anti-pattern (pseudonym_token with site_id as the key namespace)
    # must NOT reappear in any adapter.
    assert "pseudonym_token(profile.site_id" not in src, (
        f"{module_path} must not key the per-patient crypto key on site_id alone "
        f"(that defeats per-patient crypto-shred and cross-source matching)"
    )


def test_ocr_adapter_emits_canonical_token():
    """OcrAdapter, driven with a controlled natural_id, emits the canonical token.

    Proves the namespace is applied (not just imported): same (site, natural_id)
    across adapters → the same token as patient_pseudonym(site, natural_id).
    """
    from veridoc_ingestion.adapters.ocr import OcrAdapter
    from veridoc_ingestion.adapter import SourceModality, SourceProfile
    from veridoc_ingestion.ocr_engine import OcrEngine, OcrResult
    from veridoc_ingestion.blob_store import BlobStore

    class _StubEngine(OcrEngine):
        def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
            return OcrResult(
                text="x",
                document_confidence=0.99,
                word_confidences=[0.99],
                flagged=False,
                escalated=False,
            )

    class _StubBlob(BlobStore):
        def put(self, key: str, data: bytes, content_type: str) -> str:
            return f"s3://stub/{key}"

        def get(self, key: str) -> bytes:  # pragma: no cover
            return b""

    profile = SourceProfile(
        site_id=SITE,
        modality=SourceModality.OCR,
        config={"patient_id": NATURAL_ID},
    )
    adapter = OcrAdapter(ocr_engine=_StubEngine(), blob_store=_StubBlob())
    resources = adapter.ingest(b"fake-image", profile)

    doc = next(r for r in resources if r.get_resource_type() == "DocumentReference")
    # subject.reference is "Patient/<token>"
    token = doc.subject.reference.split("/", 1)[1]
    assert token == _expected_token(), (
        "OcrAdapter patient token must equal patient_pseudonym(site, natural_id) — "
        "the single canonical cross-source namespace (CR-05/SC-4)"
    )
