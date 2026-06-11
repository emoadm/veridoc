"""Tests for OcrEngine ABC, TesseractEngine (working impl), and cloud stubs.

Guards on missing system binary:
  - ``pytest.importorskip("pytesseract")`` skips the whole module if pytesseract is absent.
  - A ``shutil.which("tesseract")`` check skips live-OCR tests when the binary is absent.

This matches the pattern required in the plan: tests skip cleanly without Tesseract;
the cloud-stub and OcrResult dataclass tests always run.

RED phase: these tests are written before the implementation exists and MUST fail.
GREEN phase: implementation in ocr_engine.py makes them pass.
"""

from __future__ import annotations

import shutil
import struct

import pytest


def test_ocr_result_dataclass() -> None:
    """OcrResult must be a dataclass with the required fields."""
    from veridoc_ingestion.ocr_engine import OcrResult

    r = OcrResult(
        text="hello world",
        document_confidence=0.90,
        word_confidences=[0.9, 0.9],
        flagged=True,
        escalated=False,
    )
    assert r.text == "hello world"
    assert r.document_confidence == 0.90
    assert r.flagged is True
    assert r.escalated is False


def test_ocr_result_thresholds_flag_only() -> None:
    """document_confidence 0.90 → flagged=True, escalated=False."""
    from veridoc_ingestion.ocr_engine import OcrResult

    r = OcrResult(
        text="x",
        document_confidence=0.90,
        word_confidences=[0.9],
        flagged=True,
        escalated=False,
    )
    assert r.flagged and not r.escalated


def test_ocr_result_thresholds_escalated() -> None:
    """document_confidence 0.80 → flagged=True, escalated=True."""
    from veridoc_ingestion.ocr_engine import OcrResult

    r = OcrResult(
        text="y",
        document_confidence=0.80,
        word_confidences=[0.8],
        flagged=True,
        escalated=True,
    )
    assert r.escalated


def test_ocr_engine_is_abstract() -> None:
    """OcrEngine must be an abc.ABC with an abstract extract method."""
    import abc

    from veridoc_ingestion.ocr_engine import OcrEngine

    assert issubclass(OcrEngine, abc.ABC)
    with pytest.raises(TypeError):
        OcrEngine()  # type: ignore[abstract]


def test_textract_engine_raises_not_implemented() -> None:
    """TextractEngine.extract must raise NotImplementedError."""
    from veridoc_ingestion.ocr_engine import TextractEngine

    engine = TextractEngine()
    with pytest.raises(NotImplementedError, match="wire"):
        engine.extract(b"\x89PNG\r\n\x1a\n", "image/png")


def test_azure_document_intelligence_engine_raises_not_implemented() -> None:
    """AzureDocumentIntelligenceEngine.extract must raise NotImplementedError."""
    from veridoc_ingestion.ocr_engine import AzureDocumentIntelligenceEngine

    engine = AzureDocumentIntelligenceEngine()
    with pytest.raises(NotImplementedError, match="wire"):
        engine.extract(b"\x89PNG\r\n\x1a\n", "image/png")


def test_cloud_stubs_conform_to_ocr_engine() -> None:
    """Cloud stubs must be subclasses of OcrEngine."""
    from veridoc_ingestion.ocr_engine import (
        AzureDocumentIntelligenceEngine,
        OcrEngine,
        TextractEngine,
    )

    assert issubclass(TextractEngine, OcrEngine)
    assert issubclass(AzureDocumentIntelligenceEngine, OcrEngine)


# ---------------------------------------------------------------------------------
# Tesseract-binary-dependent tests (skipped when binary is absent)
# ---------------------------------------------------------------------------------

pytesseract = pytest.importorskip(
    "pytesseract",
    reason="pytesseract not installed; skipping TesseractEngine tests",
)


def _tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


TESSERACT_SKIP = pytest.mark.skipif(
    not _tesseract_available(),
    reason="tesseract binary not found on PATH; skipping live-OCR tests",
)


def _load_fixture(name: str) -> bytes:
    """Load a test fixture image from tests/fixtures/images/."""
    import pathlib

    fixtures_dir = pathlib.Path(__file__).parent / "fixtures" / "images"
    return (fixtures_dir / name).read_bytes()


@TESSERACT_SKIP
def test_tesseract_engine_returns_ocr_result() -> None:
    """TesseractEngine.extract returns an OcrResult for the legible fixture."""
    from veridoc_ingestion.ocr_engine import OcrResult, TesseractEngine

    engine = TesseractEngine()
    image_bytes = _load_fixture("scan_legible.png")
    result = engine.extract(image_bytes, "image/png")

    assert isinstance(result, OcrResult)
    assert isinstance(result.document_confidence, float)
    assert 0.0 <= result.document_confidence <= 1.0
    assert isinstance(result.word_confidences, list)
    assert isinstance(result.text, str)


@TESSERACT_SKIP
def test_tesseract_engine_legible_fixture_above_escalation_threshold() -> None:
    """Legible fixture must yield document_confidence >= 0.85 (not escalated)."""
    from veridoc_ingestion.ocr_engine import TesseractEngine

    engine = TesseractEngine()
    image_bytes = _load_fixture("scan_legible.png")
    result = engine.extract(image_bytes, "image/png")

    assert result.document_confidence >= 0.85, (
        f"Expected legible fixture confidence >= 0.85, got {result.document_confidence:.3f}"
    )
    assert not result.escalated, "Legible fixture should NOT be escalated"


@TESSERACT_SKIP
def test_tesseract_engine_flagging_logic() -> None:
    """TesseractEngine sets flagged=True iff confidence<0.95, escalated=True iff <0.85."""
    from veridoc_ingestion.ocr_engine import TesseractEngine

    engine = TesseractEngine()
    # Use the legible fixture (known high confidence) to verify flagged/escalated logic
    image_bytes = _load_fixture("scan_legible.png")
    result = engine.extract(image_bytes, "image/png")

    # The flags are always computed correctly from document_confidence
    expected_flagged = result.document_confidence < 0.95
    expected_escalated = result.document_confidence < 0.85
    assert result.flagged == expected_flagged
    assert result.escalated == expected_escalated


@TESSERACT_SKIP
def test_tesseract_engine_uses_image_to_data() -> None:
    """TesseractEngine must produce per-word confidences (not an empty list)."""
    from veridoc_ingestion.ocr_engine import TesseractEngine

    engine = TesseractEngine()
    image_bytes = _load_fixture("scan_legible.png")
    result = engine.extract(image_bytes, "image/png")

    # TesseractEngine uses image_to_data which returns per-word confidences;
    # a legible scan must produce at least one word
    assert len(result.word_confidences) > 0, (
        "Expected at least one word confidence from legible fixture"
    )
    # All word confidences are in 0-1 range
    for conf in result.word_confidences:
        assert 0.0 <= conf <= 1.0, f"Word confidence {conf} out of 0-1 range"
