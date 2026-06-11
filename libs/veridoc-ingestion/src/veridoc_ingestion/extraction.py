"""Clinical-entity extraction interface (D-09).

Defines :class:`EntityExtractor` (ABC) and :class:`RuleBasedExtractor` (the default
rule-based implementation for this phase). The interface is designed so a future
LLM-backed extractor (Phase 4) can be swapped in as a drop-in replacement without
touching the adapters (D-09 deferral honored).

**Scope constraint:** :class:`RuleBasedExtractor` is rule-based ONLY. It extracts
structured data from text using regex/keyword patterns. It does NOT call any LLM,
language model, or ML service (D-09: LLM extraction is explicitly deferred to Phase 4).

Architecture
------------
- :class:`EntityExtractor` is an ABC with a single abstract method :meth:`extract`.
- :class:`RuleBasedExtractor` implements heuristic lab-result extraction from text:
  it looks for patterns like ``Creatinine: 0.9 mg/dL`` and maps them to FHIR
  ``Observation`` dicts using a small LOINC lookup table for common lab tests.

Pattern analog: :class:`veridoc_ingestion.ocr_engine.OcrEngine` (ABC + concrete default
with stub cloud engines for Phase 4 replacement).

Usage::

    extractor = RuleBasedExtractor()
    results = extractor.extract(text="Creatinine: 0.9 mg/dL [Ref: 0.7-1.3] NORMAL")
    # results → [{"resourceType": "Observation", "code": {"coding": [{"code": "2160-0", ...}]}, ...}]
"""

from __future__ import annotations

import abc
import re

__all__ = ["EntityExtractor", "RuleBasedExtractor"]


class EntityExtractor(abc.ABC):
    """Abstract clinical-entity extractor (D-09 interface).

    Concrete implementations:
    - :class:`RuleBasedExtractor` — regex/keyword rule-based (this phase; D-09).
    - LlmEntityExtractor — Phase 4 LLM-backed extractor (not yet built).
    """

    @abc.abstractmethod
    def extract(self, text: str) -> list[dict]:
        """Extract clinical entities from ``text``; return FHIR R4B resource dicts.

        Args:
            text: Plain text to analyze (OCR output or PDF/Excel text dump).

        Returns:
            List of FHIR R4B resource dicts (not model instances; caller validates).
            May include Observation, Condition, MedicationRequest, etc.
        """


# ---------------------------------------------------------------------------
# LOINC lookup table for common lab tests (rule-based; no LLM — D-09)
# ---------------------------------------------------------------------------
# Mapping from lowercase keyword → (loinc_code, display, unit_code, ucum_system)
_LAB_LOINC_MAP: dict[str, tuple[str, str, str, str]] = {
    "creatinine": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma", "mg/dL", "http://unitsofmeasure.org"),
    "sodium": ("2951-2", "Sodium [Moles/volume] in Serum or Plasma", "mmol/L", "http://unitsofmeasure.org"),
    "potassium": ("2823-3", "Potassium [Moles/volume] in Serum or Plasma", "mmol/L", "http://unitsofmeasure.org"),
    "glucose": ("2345-7", "Glucose [Mass/volume] in Serum or Plasma", "mg/dL", "http://unitsofmeasure.org"),
    "hemoglobin": ("718-7", "Hemoglobin [Mass/volume] in Blood", "g/dL", "http://unitsofmeasure.org"),
    "hematocrit": ("4544-3", "Hematocrit [Volume Fraction] of Blood by Automated count", "%", "http://unitsofmeasure.org"),
    "wbc": ("6690-2", "Leukocytes [#/volume] in Blood by Automated count", "10*3/uL", "http://unitsofmeasure.org"),
    "platelets": ("777-3", "Platelets [#/volume] in Blood by Automated count", "10*3/uL", "http://unitsofmeasure.org"),
    "cholesterol": ("2093-3", "Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL", "http://unitsofmeasure.org"),
    "triglycerides": ("2571-8", "Triglycerides [Mass/volume] in Serum or Plasma", "mg/dL", "http://unitsofmeasure.org"),
    "blood pressure": ("55284-4", "Blood pressure systolic and diastolic", "mm[Hg]", "http://unitsofmeasure.org"),
}

# Regex to detect lab results: "TestName: value unit" or "TestName value unit"
# Matches: "Creatinine: 0.9 mg/dL", "Sodium 138 mmol/L", "Creatinine: 0.9 mg/dL [Ref: ...]"
_LAB_LINE_RE = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z\s]{2,30}?)[:]\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>[A-Za-z%/*\[\]]+(?:/[A-Za-z%/*\[\]]+)?)?"
    r"(?:\s+\[Ref:[^\]]+\])?"
    r"(?:\s+(?P<status>NORMAL|ABNORMAL|HIGH|LOW|CRITICAL))?",
    re.IGNORECASE,
)


class RuleBasedExtractor(EntityExtractor):
    """Rule-based clinical-entity extractor (D-09 — no LLM calls this phase).

    Extracts lab results from plain text using regex patterns and a LOINC lookup
    table for common lab analytes. Only extracts Observation resources for now;
    other entity types (Condition, Medication) are deferred to Phase 4 LLM extraction.

    **Security:** Text is analyzed in-process only; no external calls are made.
    """

    def extract(self, text: str) -> list[dict]:
        """Extract Observation candidates from ``text`` using regex + LOINC lookup.

        Args:
            text: Plain text from PDF extraction or OCR output.

        Returns:
            List of Observation resource dicts (without subject — caller must set).
            Empty list if no recognized lab patterns are found.
        """
        import uuid

        results: list[dict] = []

        for match in _LAB_LINE_RE.finditer(text):
            name_raw = match.group("name").strip().lower().rstrip(":")
            value_str = match.group("value")
            unit_raw = match.group("unit") or ""
            status_raw = match.group("status") or ""

            # Look up LOINC entry for this analyte name
            loinc_entry = None
            for keyword, entry in _LAB_LOINC_MAP.items():
                if keyword in name_raw:
                    loinc_entry = entry
                    break

            if loinc_entry is None:
                continue  # unknown analyte; skip (rule-based: no guessing)

            loinc_code, loinc_display, expected_unit, unit_system = loinc_entry
            unit_code = unit_raw.strip() or expected_unit

            # Build Observation dict (fhir.resources format)
            try:
                numeric_val = float(value_str)
            except ValueError:
                continue

            # Observation status: NORMAL → "final"; ABNORMAL/HIGH/LOW → "final" (status is in interpretation)
            obs_status = "final"

            obs_dict: dict = {
                "resourceType": "Observation",
                "id": str(uuid.uuid4()),
                "status": obs_status,
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": loinc_code,
                            "display": loinc_display,
                        }
                    ],
                    "text": loinc_display,
                },
                "valueQuantity": {
                    "value": numeric_val,
                    "unit": unit_code,
                    "system": unit_system,
                    "code": unit_code,
                },
            }

            # Add interpretation if status provided
            if status_raw.upper() in ("ABNORMAL", "HIGH", "LOW", "CRITICAL"):
                interp_code = {"ABNORMAL": "A", "HIGH": "H", "LOW": "L", "CRITICAL": "AA"}.get(
                    status_raw.upper(), "A"
                )
                obs_dict["interpretation"] = [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": interp_code,
                            }
                        ]
                    }
                ]

            results.append(obs_dict)

        return results
