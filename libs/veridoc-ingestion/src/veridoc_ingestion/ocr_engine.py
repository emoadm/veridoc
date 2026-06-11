"""Provider-portable OCR abstraction (D-07/D-08).

Mirrors the KMSKeyring pattern in veridoc-crypto/kms.py exactly:

  - :class:`OcrEngine` — the ABC (mirrors ``KMSKeyring``).
  - :class:`TesseractEngine` — the working implementation (mirrors ``LocalKeyring``);
    requires the ``tesseract-ocr`` system package and ``pytesseract`` Python wrapper.
  - :class:`TextractEngine` — AWS Textract stub (mirrors ``AwsKmsKeyring``); raises
    :exc:`NotImplementedError` until DEC-cloud-provider closes to AWS.
  - :class:`AzureDocumentIntelligenceEngine` — Azure stub (mirrors ``AzureKeyVaultKeyring``);
    raises :exc:`NotImplementedError` until DEC-cloud-provider closes to Azure.

ALCOA+ legibility thresholds (D-09, SC-3):
  - ``flagged``   = ``document_confidence < 0.95``  → legibility flag; human review advisable.
  - ``escalated`` = ``document_confidence < 0.85``  → legibility escalate; must go to human.

``document_confidence`` is the arithmetic mean of per-word confidence scores returned by
``pytesseract.image_to_data(..., output_type=Output.DICT)``, filtered to exclude the
block/paragraph/line-level entries (``conf == -1``) and blank tokens.  Scores are on the
Tesseract 0–100 scale and are divided by 100 to produce the 0.0–1.0 range stored in
:class:`OcrResult`.

Security: document bytes are only read as image data by PIL/pytesseract, never executed
(T-02-OCR-02).  ALCOA flags are computed server-side from raw pytesseract output and are
never user-supplied (T-02-OCR-01).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

__all__ = [
    "OcrEngine",
    "OcrResult",
    "TesseractEngine",
    "TextractEngine",
    "AzureDocumentIntelligenceEngine",
]


@dataclass
class OcrResult:
    """Result of an OCR extraction with ALCOA+ legibility flags.

    Attributes:
        text: Reconstructed full text (words joined with spaces).
        document_confidence: Mean per-word confidence, 0.0–1.0 scale.
        word_confidences: Raw per-word confidence values (0.0–1.0 each).
        flagged: ``True`` if ``document_confidence < 0.95`` (ALCOA-01 legibility flag).
        escalated: ``True`` if ``document_confidence < 0.85`` (escalate to human review).
    """

    text: str
    document_confidence: float
    word_confidences: list[float]
    flagged: bool
    escalated: bool


class OcrEngine(abc.ABC):
    """Provider-portable OCR abstraction (mirrors KMSKeyring in veridoc-crypto).

    Implementations: TesseractEngine (default), TextractEngine, AzureDocumentIntelligenceEngine.
    """

    @abc.abstractmethod
    def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        """Run OCR on ``image_bytes``; return an :class:`OcrResult` with confidence.

        Args:
            image_bytes: Raw image bytes (PNG, TIFF, JPEG …).
            content_type: MIME type of the image (e.g. ``"image/png"``).

        Returns:
            :class:`OcrResult` with per-word and document-level confidence and ALCOA flags.
        """


class TesseractEngine(OcrEngine):
    """Tesseract OCR via pytesseract (D-08).

    Requires the ``tesseract-ocr`` and ``tesseract-ocr-eng`` system packages.  In
    Docker/CI, install with ``apt-get install -y tesseract-ocr tesseract-ocr-eng``.

    Uses ``pytesseract.image_to_data`` (TSV mode) to obtain per-word confidence
    scores rather than a subprocess call — see RESEARCH.md §"Don't Hand-Roll".

    Security: image bytes are opened by PIL and read by pytesseract as image data
    only; they are never evaluated or executed (T-02-OCR-02 mitigated).
    """

    def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:  # noqa: ARG002
        """Extract text and confidence from ``image_bytes`` using Tesseract.

        Args:
            image_bytes: Raw image bytes (any PIL-supported format).
            content_type: MIME type (informational; PIL auto-detects format).

        Returns:
            :class:`OcrResult` with ``document_confidence`` in 0.0–1.0 and
            ALCOA legibility flags at the 0.95 / 0.85 thresholds.
        """
        import io

        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Filter block/paragraph/line-level entries (conf == -1) and blank tokens.
        # Tesseract returns confidence on a 0–100 scale; divide by 100 for 0.0–1.0.
        word_confs = [
            c / 100.0
            for c, txt in zip(data["conf"], data["text"])
            if c != -1 and str(txt).strip()
        ]
        doc_conf = sum(word_confs) / len(word_confs) if word_confs else 0.0
        full_text = " ".join(t for t in data["text"] if str(t).strip())

        return OcrResult(
            text=full_text,
            document_confidence=doc_conf,
            word_confidences=word_confs,
            flagged=doc_conf < 0.95,
            escalated=doc_conf < 0.85,
        )


class TextractEngine(OcrEngine):  # pragma: no cover - DEC-cloud-provider OPEN
    """AWS Textract adapter (interface stub this phase; DEC-cloud-provider OPEN).

    When DEC-cloud-provider closes to AWS, this wires the AWS Textract API so OCR
    extraction uses a managed cloud service rather than the local Tesseract binary.
    """

    def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        raise NotImplementedError(
            "TextractEngine is a portability stub this phase; wire AWS Textract "
            "when DEC-cloud-provider closes to AWS"
        )


class AzureDocumentIntelligenceEngine(OcrEngine):  # pragma: no cover - DEC-cloud-provider OPEN
    """Azure Document Intelligence adapter (interface stub this phase; DEC-cloud-provider OPEN).

    When DEC-cloud-provider closes to Azure, this wires the Azure Document Intelligence
    API so OCR extraction uses a managed cloud service rather than the local Tesseract binary.
    """

    def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
        raise NotImplementedError(
            "AzureDocumentIntelligenceEngine is a portability stub this phase; wire "
            "Azure Document Intelligence when DEC-cloud-provider closes to Azure"
        )
