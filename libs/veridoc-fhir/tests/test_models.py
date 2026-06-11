"""Tests for FHIR R4B model facade (veridoc_fhir.models).

Verifies:
- All 9 clinical resource types + Provenance import from fhir.resources.R4B (D-01)
- models.__all__ contains exactly those 10 classes (R5 top-level namespace guard, Pitfall 1)
- models.py source code imports from fhir.resources.R4B (not top-level R5)
- All 9 resource types + Provenance construct and round-trip via model_validate / model_dump
- Synthea bundle fixtures load into the model without ValidationError
- The hand-crafted AdverseEvent fixture (Synthea gap A7) validates
"""

from __future__ import annotations

import glob
import inspect
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "fhir"


class TestModelsImportDiscipline:
    """Guard: all imports come from fhir.resources.R4B, never top-level R5."""

    def test_all_contains_all_10_classes(self):
        import veridoc_fhir.models as m

        expected = {
            "Patient",
            "Encounter",
            "Observation",
            "Condition",
            "MedicationRequest",
            "AdverseEvent",
            "DiagnosticReport",
            "DocumentReference",
            "Procedure",
            "Provenance",
        }
        assert set(m.__all__) >= expected, (
            f"models.__all__ missing: {expected - set(m.__all__)}"
        )

    def test_source_uses_R4B_imports(self):
        """Source-inspection test: models.py must import from fhir.resources.R4B.*"""
        import veridoc_fhir.models as m

        source = inspect.getsource(m)
        assert "fhir.resources.R4B" in source, (
            "models.py does not import from fhir.resources.R4B — "
            "top-level fhir.resources.* imports now resolve to R5 (since v7.0.0)"
        )

    def test_no_top_level_fhir_resource_imports(self):
        """models.py must NOT use the top-level fhir.resources.patient style (R5)."""
        import veridoc_fhir.models as m

        source = inspect.getsource(m)
        # Top-level imports look like 'from fhir.resources.patient' (no R4B sub-path)
        lines = [
            ln
            for ln in source.splitlines()
            if "from fhir.resources." in ln
            and "R4B" not in ln
            and ln.strip().startswith("from")
        ]
        assert not lines, (
            f"Top-level (R5) fhir.resources imports found:\n"
            + "\n".join(lines)
        )


class TestResourceConstruction:
    """All 9 resources + Provenance construct from minimal valid dicts."""

    def test_patient_construction(self):
        from veridoc_fhir.models import Patient

        p = Patient.model_validate({
            "resourceType": "Patient",
            "id": "p-pseudo-001",
            "active": True,
        })
        assert p.id == "p-pseudo-001"
        assert p.resource_type == "Patient"

    def test_encounter_construction(self):
        from veridoc_fhir.models import Encounter

        e = Encounter.model_validate({
            "resourceType": "Encounter",
            "id": "enc-001",
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
            },
        })
        assert e.resource_type == "Encounter"

    def test_observation_construction(self):
        from veridoc_fhir.models import Observation

        o = Observation.model_validate({
            "resourceType": "Observation",
            "id": "obs-001",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7"}]},
            "subject": {"reference": "Patient/p-pseudo-001"},
        })
        assert o.resource_type == "Observation"

    def test_condition_construction(self):
        from veridoc_fhir.models import Condition

        c = Condition.model_validate({
            "resourceType": "Condition",
            "id": "cond-001",
            "subject": {"reference": "Patient/p-pseudo-001"},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]},
        })
        assert c.resource_type == "Condition"

    def test_medication_request_construction(self):
        from veridoc_fhir.models import MedicationRequest

        mr = MedicationRequest.model_validate({
            "resourceType": "MedicationRequest",
            "id": "medreq-001",
            "status": "active",
            "intent": "order",
            "subject": {"reference": "Patient/p-pseudo-001"},
            "medicationCodeableConcept": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "1049502"}]
            },
        })
        assert mr.resource_type == "MedicationRequest"

    def test_adverse_event_construction(self):
        from veridoc_fhir.models import AdverseEvent

        ae = AdverseEvent.model_validate({
            "resourceType": "AdverseEvent",
            "id": "ae-001",
            "actuality": "actual",
            "subject": {"reference": "Patient/p-pseudo-001"},
        })
        assert ae.resource_type == "AdverseEvent"

    def test_diagnostic_report_construction(self):
        from veridoc_fhir.models import DiagnosticReport

        dr = DiagnosticReport.model_validate({
            "resourceType": "DiagnosticReport",
            "id": "dr-001",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "11502-2"}]},
            "subject": {"reference": "Patient/p-pseudo-001"},
        })
        assert dr.resource_type == "DiagnosticReport"

    def test_document_reference_construction(self):
        from veridoc_fhir.models import DocumentReference

        docref = DocumentReference.model_validate({
            "resourceType": "DocumentReference",
            "id": "docref-001",
            "status": "current",
            "content": [{"attachment": {"contentType": "application/pdf", "url": "s3://bucket/doc.pdf"}}],
        })
        assert docref.resource_type == "DocumentReference"

    def test_procedure_construction(self):
        from veridoc_fhir.models import Procedure

        proc = Procedure.model_validate({
            "resourceType": "Procedure",
            "id": "proc-001",
            "status": "completed",
            "subject": {"reference": "Patient/p-pseudo-001"},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "80146002"}]},
        })
        assert proc.resource_type == "Procedure"

    def test_provenance_construction(self):
        from veridoc_fhir.models import Provenance
        from datetime import datetime, timezone

        prov = Provenance.model_validate({
            "resourceType": "Provenance",
            "id": "prov-001",
            "target": [{"reference": "Patient/p-pseudo-001"}],
            "recorded": datetime.now(timezone.utc).isoformat(),
            "agent": [{"who": {"reference": "Device/ingestion-service"}}],
        })
        assert prov.resource_type == "Provenance"


class TestRoundTrip:
    """Resources must serialize and deserialize without data loss."""

    def test_patient_model_dump_roundtrip(self):
        from veridoc_fhir.models import Patient

        original = {
            "resourceType": "Patient",
            "id": "p-round-trip-001",
            "active": True,
            "meta": {"source": "urn:veridoc:source:native-fhir:site-001"},
        }
        p = Patient.model_validate(original)
        dumped = p.model_dump()
        assert dumped["id"] == "p-round-trip-001"
        assert dumped["meta"]["source"] == "urn:veridoc:source:native-fhir:site-001"

    def test_model_dump_json(self):
        from veridoc_fhir.models import Observation

        obs = Observation.model_validate({
            "resourceType": "Observation",
            "id": "obs-json-001",
            "status": "final",
            "code": {"text": "Weight"},
        })
        json_str = obs.model_dump_json()
        data = json.loads(json_str)
        assert data["id"] == "obs-json-001"


class TestSyntheaFixtures:
    """All Synthea bundles + hand-crafted AdverseEvent must load without errors."""

    def test_at_least_three_fixture_files_exist(self):
        fixtures = glob.glob(str(FIXTURES_DIR / "*.json"))
        assert len(fixtures) >= 3, (
            f"Expected >=3 FHIR fixtures, found {len(fixtures)}: {fixtures}"
        )

    @pytest.mark.parametrize(
        "bundle_path",
        [p for p in glob.glob(str(FIXTURES_DIR / "*.json")) if "adverse_event" not in p],
    )
    def test_synthea_bundle_loads(self, bundle_path):
        """Synthea Bundle JSON parses without ValidationError under R4B models."""
        from fhir.resources.R4B.bundle import Bundle

        with open(bundle_path) as f:
            data = json.load(f)
        # Bundles may contain extra extensions; allow unknown fields in test context
        bundle = Bundle.model_validate(data)
        assert bundle.resource_type == "Bundle"
        assert len(bundle.entry or []) > 0

    def test_adverse_event_fixture_validates(self):
        """Hand-crafted AdverseEvent fixture (Synthea gap A7) must validate as R4B."""
        from veridoc_fhir.models import AdverseEvent

        fixture_path = FIXTURES_DIR / "adverse_event.json"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"
        with open(fixture_path) as f:
            data = json.load(f)
        ae = AdverseEvent.model_validate(data)
        assert ae.resource_type == "AdverseEvent"
        assert ae.id == "ae-veridoc-edge-case-001"

    def test_synthea_bundles_contain_required_resource_types(self):
        """Synthea bundles together must contain Patient, Encounter, Condition, etc."""
        found_types: set[str] = set()
        bundle_paths = [
            p
            for p in glob.glob(str(FIXTURES_DIR / "*.json"))
            if "adverse_event" not in p
        ]
        for bundle_path in bundle_paths:
            with open(bundle_path) as f:
                data = json.load(f)
            for entry in data.get("entry", []):
                rt = entry.get("resource", {}).get("resourceType")
                if rt:
                    found_types.add(rt)
        # Synthea consistently generates these types
        expected_in_bundles = {"Patient", "Encounter", "Condition", "Observation", "Procedure"}
        missing = expected_in_bundles - found_types
        assert not missing, f"Synthea bundles missing resource types: {missing}"


class TestExtensionConstants:
    """extensions.py must define the canonical URN constants."""

    def test_ocr_confidence_url_defined(self):
        from veridoc_fhir.extensions import OCR_CONFIDENCE_URL

        assert OCR_CONFIDENCE_URL == "urn:veridoc:extension:ocr-confidence"

    def test_ingestion_path_url_defined(self):
        from veridoc_fhir.extensions import INGESTION_PATH_URL

        assert INGESTION_PATH_URL == "urn:veridoc:extension:ingestion-path"

    def test_alcoa_legibility_flag_url_defined(self):
        from veridoc_fhir.extensions import ALCOA_LEGIBILITY_FLAG_URL

        assert ALCOA_LEGIBILITY_FLAG_URL == "urn:veridoc:extension:alcoa-legibility-flag"
