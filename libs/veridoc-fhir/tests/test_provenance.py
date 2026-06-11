"""Tests for the FHIR Provenance factory (veridoc_fhir.provenance).

Verifies:
- create_provenance() returns a valid R4B Provenance (D-03)
- meta.source is carried on the Provenance entity reference
- recorded is a timezone-aware ISO 8601 instant (Pitfall 9)
- ingestion-path extension is always present
- ocr-confidence extension present only when ocr_confidence is not None
- agent.who.reference is set correctly
- target reference is correct
"""

from __future__ import annotations

import json
from datetime import timezone

import pytest


class TestCreateProvenanceBasic:
    """create_provenance() produces a valid Provenance resource."""

    def test_returns_provenance_instance(self):
        from veridoc_fhir.provenance import create_provenance

        prov = create_provenance(
            target_ref="Patient/p-pseudo-001",
            source="urn:veridoc:source:native-fhir:site-001",
            ingestion_path="native-fhir",
            actor_ref="Device/ingestion-service",
        )
        assert prov.resource_type == "Provenance"

    def test_target_reference_set(self):
        from veridoc_fhir.provenance import create_provenance

        prov = create_provenance(
            target_ref="Patient/p-pseudo-001",
            source="urn:veridoc:source:native-fhir:site-001",
            ingestion_path="native-fhir",
            actor_ref="Device/ingestion-service",
        )
        assert len(prov.target) == 1
        assert prov.target[0].reference == "Patient/p-pseudo-001"

    def test_agent_who_reference_set(self):
        from veridoc_fhir.provenance import create_provenance

        prov = create_provenance(
            target_ref="Patient/p-pseudo-001",
            source="urn:veridoc:source:native-fhir:site-001",
            ingestion_path="native-fhir",
            actor_ref="Device/ingestion-service",
        )
        assert len(prov.agent) == 1
        assert prov.agent[0].who.reference == "Device/ingestion-service"

    def test_entity_source_reference_set(self):
        """entity.what.reference must carry the pseudonymized source reference."""
        from veridoc_fhir.provenance import create_provenance

        source = "urn:veridoc:source:native-fhir:site-001"
        prov = create_provenance(
            target_ref="Patient/p-pseudo-001",
            source=source,
            ingestion_path="native-fhir",
            actor_ref="Device/ingestion-service",
        )
        assert len(prov.entity) == 1
        assert prov.entity[0].role == "source"
        assert prov.entity[0].what.reference == source


class TestCreateProvenanceRecorded:
    """recorded must be a timezone-aware ISO instant (Pitfall 9)."""

    def test_recorded_is_not_none(self):
        from veridoc_fhir.provenance import create_provenance

        prov = create_provenance(
            target_ref="Patient/p-001",
            source="urn:veridoc:source:test",
            ingestion_path="test",
            actor_ref="Device/test",
        )
        assert prov.recorded is not None

    def test_recorded_is_timezone_aware(self):
        """Provenance.recorded must not be a naive datetime — Pitfall 9 guard."""
        from veridoc_fhir.provenance import create_provenance

        prov = create_provenance(
            target_ref="Patient/p-001",
            source="urn:veridoc:source:test",
            ingestion_path="test",
            actor_ref="Device/test",
        )
        # fhir.resources returns recorded as a string (ISO instant)
        # or a datetime object — either way we can verify tz-awareness
        recorded = prov.recorded
        if hasattr(recorded, "tzinfo"):
            assert recorded.tzinfo is not None, (
                "Provenance.recorded is a naive datetime — must be tz-aware (Pitfall 9)"
            )
        else:
            # It's a string — ensure it ends with Z or ±HH:MM (tz offset present)
            recorded_str = str(recorded)
            assert (
                recorded_str.endswith("Z")
                or "+" in recorded_str[10:]
                or "-" in recorded_str[10:]
            ), f"Provenance.recorded '{recorded_str}' has no timezone offset (Pitfall 9)"


class TestCreateProvenanceExtensions:
    """Extension behaviour: ingestion-path always present; ocr-confidence conditional."""

    def test_ingestion_path_extension_always_present(self):
        from veridoc_fhir.provenance import create_provenance
        from veridoc_fhir.extensions import INGESTION_PATH_URL

        prov = create_provenance(
            target_ref="Patient/p-001",
            source="urn:veridoc:source:hl7v2:site-002",
            ingestion_path="hl7v2",
            actor_ref="Device/ingestion-service",
        )
        extensions = prov.extension or []
        path_exts = [e for e in extensions if e.url == INGESTION_PATH_URL]
        assert len(path_exts) == 1, (
            f"Expected 1 ingestion-path extension, found {len(path_exts)}"
        )
        assert path_exts[0].valueString == "hl7v2"

    def test_ocr_confidence_extension_absent_when_not_passed(self):
        from veridoc_fhir.provenance import create_provenance
        from veridoc_fhir.extensions import OCR_CONFIDENCE_URL

        prov = create_provenance(
            target_ref="Patient/p-001",
            source="urn:veridoc:source:native-fhir:site-001",
            ingestion_path="native-fhir",
            actor_ref="Device/ingestion-service",
            # ocr_confidence NOT passed
        )
        extensions = prov.extension or []
        ocr_exts = [e for e in extensions if e.url == OCR_CONFIDENCE_URL]
        assert len(ocr_exts) == 0, (
            "ocr-confidence extension must not be present when ocr_confidence is None"
        )

    def test_ocr_confidence_extension_present_when_passed(self):
        from veridoc_fhir.provenance import create_provenance
        from veridoc_fhir.extensions import OCR_CONFIDENCE_URL

        prov = create_provenance(
            target_ref="Patient/p-001",
            source="urn:veridoc:source:ocr:site-003",
            ingestion_path="ocr",
            actor_ref="Device/ingestion-service",
            ocr_confidence=0.97,
        )
        extensions = prov.extension or []
        ocr_exts = [e for e in extensions if e.url == OCR_CONFIDENCE_URL]
        assert len(ocr_exts) == 1, (
            "ocr-confidence extension must be present when ocr_confidence is passed"
        )
        assert abs(ocr_exts[0].valueDecimal - 0.97) < 1e-6

    def test_ocr_confidence_zero_is_present(self):
        """0.0 is a valid confidence value (very poor OCR) — not falsy-None."""
        from veridoc_fhir.provenance import create_provenance
        from veridoc_fhir.extensions import OCR_CONFIDENCE_URL

        prov = create_provenance(
            target_ref="Patient/p-001",
            source="urn:veridoc:source:ocr:site-003",
            ingestion_path="ocr",
            actor_ref="Device/ingestion-service",
            ocr_confidence=0.0,
        )
        extensions = prov.extension or []
        ocr_exts = [e for e in extensions if e.url == OCR_CONFIDENCE_URL]
        assert len(ocr_exts) == 1


class TestCreateProvenanceSerialization:
    """Provenance must round-trip through JSON."""

    def test_provenance_model_dump_json(self):
        from veridoc_fhir.provenance import create_provenance

        prov = create_provenance(
            target_ref="Patient/p-pseudo-001",
            source="urn:veridoc:source:native-fhir:site-001",
            ingestion_path="native-fhir",
            actor_ref="Device/ingestion-service",
            ocr_confidence=0.88,
        )
        json_str = prov.model_dump_json()
        data = json.loads(json_str)
        assert data["resourceType"] == "Provenance"
        assert data["target"][0]["reference"] == "Patient/p-pseudo-001"

    def test_provenance_meta_source_is_set(self):
        """meta.source on the Provenance itself reflects the ingestion source URN."""
        from veridoc_fhir.provenance import create_provenance

        source = "urn:veridoc:source:native-fhir:site-001"
        prov = create_provenance(
            target_ref="Patient/p-pseudo-001",
            source=source,
            ingestion_path="native-fhir",
            actor_ref="Device/ingestion-service",
        )
        # meta.source is set on the Provenance resource itself
        assert prov.meta is not None
        assert prov.meta.source == source
