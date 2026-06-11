"""PdfExcelAdapter — structured PDF/Excel → FHIR R4B resources (D-11, SC-2b).

Parses structured PDFs (via ``pypdf``) and Excel workbooks (via ``openpyxl``) using
the rule-based :class:`~veridoc_ingestion.extraction.RuleBasedExtractor`, then builds
FHIR R4B resources from the extracted entities. Patient PII is pseudonymized via
``pseudonym_token`` (D-14).

The adapter detects format by attempting Excel parse first (openpyxl), then falls
back to PDF (pypdf). Unknown formats raise ``ValueError`` with a clear message.

**Threat mitigations:**
- T-02-ADP-03 (zip-bomb / malformed PDF/Excel): pypdf/openpyxl read-only parsing;
  both raise ``Exception`` on malformed input which we catch and re-raise as
  ``ValueError``. Size/content bounds are enforced at the service layer (not here).
- T-02-ADP-01 (PII disclosure): Patient name from PDF is replaced by pseudonym token;
  raw MRN replaced before returning resources.

Pattern analog: :class:`~veridoc_ingestion.adapters.native_fhir.NativeFhirAdapter`
(same pseudonymization discipline; same list[fhir.resources.R4B model] return type).
"""

from __future__ import annotations

import io
import uuid

from ..adapter import SourceAdapter, SourceProfile
from ..extraction import RuleBasedExtractor

__all__ = ["PdfExcelAdapter"]

# Default extractor (rule-based only this phase — D-09)
_EXTRACTOR = RuleBasedExtractor()


def _extract_pdf_text(payload: bytes) -> str:
    """Extract plain text from a PDF payload.

    Args:
        payload: Raw PDF bytes.

    Returns:
        Concatenated text from all pages.

    Raises:
        ValueError: If the payload is not a valid PDF.
    """
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(payload))
        pages_text = []
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")
        return "\n".join(pages_text)
    except Exception as exc:
        raise ValueError(f"PdfExcelAdapter: PDF parse failed — {exc}") from exc


def _extract_excel_rows(payload: bytes) -> str:
    """Extract plain text from an Excel (.xlsx) payload.

    Reads all sheets and concatenates cell values as a flat text dump.

    Args:
        payload: Raw Excel (.xlsx) bytes.

    Returns:
        Tab/newline separated cell values as plain text.

    Raises:
        ValueError: If the payload is not a valid xlsx file.
    """
    try:
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
        rows_text: list[str] = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                row_vals = [str(c) if c is not None else "" for c in row]
                rows_text.append("\t".join(row_vals))
        wb.close()
        return "\n".join(rows_text)
    except Exception as exc:
        raise ValueError(f"PdfExcelAdapter: Excel parse failed — {exc}") from exc


def _is_xlsx(payload: bytes) -> bool:
    """Return True if payload looks like an xlsx (ZIP-based Office Open XML)."""
    # xlsx files start with the ZIP magic bytes PK\x03\x04
    return payload[:4] == b"PK\x03\x04"


def _extract_mrn_from_text(text: str) -> str | None:
    """Heuristic: extract MRN from PDF/Excel text if present.

    Looks for 'MRN: VALUE' or 'MRN VALUE' patterns.

    Returns:
        The MRN string if found, else None.
    """
    import re

    m = re.search(r"MRN[:\s]+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


class PdfExcelAdapter(SourceAdapter):
    """PDF/Excel → FHIR R4B adapter using rule-based entity extraction (D-11, SC-2b).

    Accepts both ``application/pdf`` and ``application/vnd.openxmlformats-officedocument.
    spreadsheetml.sheet`` payloads. Format is auto-detected from the payload bytes.

    Pseudonymizes Patient PII (name, MRN) via ``pseudonym_token`` before returning
    resources (D-14, SC-4). The patient_id is derived from ``profile.site_id`` +
    MRN found in the document; falls back to a random UUID if no MRN is detected.

    The rule-based extractor is the default (D-09); it can be replaced by injecting
    a custom :class:`~veridoc_ingestion.extraction.EntityExtractor` at construction.
    """

    def __init__(self, extractor=None) -> None:
        """Initialize with an optional custom extractor.

        Args:
            extractor: An :class:`~veridoc_ingestion.extraction.EntityExtractor`
                       instance. Defaults to :class:`~veridoc_ingestion.extraction.RuleBasedExtractor`.
        """
        self._extractor = extractor or _EXTRACTOR

    def ingest(self, payload: bytes, profile: SourceProfile) -> list:
        """Parse a PDF or Excel payload; return pseudonymized R4B resource list.

        Args:
            payload: Raw PDF or xlsx bytes.
            profile: Site profile (site_id used as namespace prefix).

        Returns:
            List of ``fhir.resources.R4B`` model instances.

        Raises:
            ValueError: If the payload cannot be parsed as PDF or xlsx.
        """
        from fhir.resources.R4B.observation import Observation
        from fhir.resources.R4B.patient import Patient
        from veridoc_pseudonym import pseudonym_token

        # Auto-detect format and extract text
        if _is_xlsx(payload):
            text = _extract_excel_rows(payload)
        else:
            text = _extract_pdf_text(payload)

        # Extract MRN from text for pseudonymization
        natural_id = _extract_mrn_from_text(text) or str(uuid.uuid4())
        patient_id = pseudonym_token(profile.site_id, natural_id)

        # Run rule-based extraction → list of FHIR resource dicts
        entity_dicts = self._extractor.extract(text)

        resources: list = []

        # Build a Patient resource (pseudonymized)
        patient = Patient.model_validate({
            "resourceType": "Patient",
            "id": patient_id,
            "meta": {
                "source": f"urn:veridoc:source:pdf-excel:{profile.site_id}",
            },
            "identifier": [
                {
                    "system": "urn:veridoc:pseudonym",
                    "value": patient_id,
                }
            ],
            "name": [{"text": "PSEUDONYMIZED"}],
            "active": True,
        })
        resources.append(patient)

        # Build FHIR models from extractor output; inject subject reference
        for entity_dict in entity_dicts:
            res_type = entity_dict.get("resourceType", "")

            if res_type == "Observation":
                entity_dict = dict(entity_dict)
                entity_dict["subject"] = {"reference": f"Patient/{patient_id}"}
                try:
                    obs = Observation.model_validate(entity_dict)
                    resources.append(obs)
                except Exception:  # noqa: BLE001
                    # Skip observations that fail R4B validation
                    continue

        return resources
