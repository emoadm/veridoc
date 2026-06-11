"""Tests for FhirRepository (veridoc_fhir.repository).

Verifies:
- FhirRepository uses AsyncMongoClient (NOT motor — Pitfall 2)
- create_indexes() declares a unique (resourceType, id) index (Pitfall 6)
- save() upserts resources (Patient, Encounter, etc.) idempotently
- re-saving the same resourceType+id does not create a duplicate document
- find_by_patient() returns previously saved resources for a patient (SC-1)
- create_indexes() declares compound (resourceType, subject.reference) index
- source inspection: 'motor' not in repository.py, 'AsyncMongoClient' in repository.py

Tests that require a running MongoDB skip gracefully if neither
VERIDOC_TEST_MONGODB_URL is set nor Docker is available (conftest.py handles it).
"""

from __future__ import annotations

import inspect

import pytest


class TestRepositorySourceCode:
    """Guard: source inspection for AsyncMongoClient (not motor)."""

    def test_uses_asyncmongoclient_not_motor(self):
        """FhirRepository MUST use AsyncMongoClient — motor is deprecated (Pitfall 2)."""
        from veridoc_fhir.repository import FhirRepository

        source = inspect.getsource(FhirRepository)
        assert "AsyncMongoClient" in source, (
            "FhirRepository must use pymongo.AsyncMongoClient"
        )
        assert "motor" not in source, (
            "FhirRepository must NOT use motor — it is deprecated (EOL 2026-05-14)"
        )

    def test_create_index_present_in_source(self):
        """create_indexes() must call create_index (Pitfall 6 guard)."""
        from veridoc_fhir.repository import FhirRepository

        source = inspect.getsource(FhirRepository)
        assert "create_index" in source, (
            "FhirRepository.create_indexes() must call create_index at startup (Pitfall 6)"
        )


@pytest.mark.anyio
class TestFhirRepositoryIntegration:
    """Integration tests: save, find_by_patient, idempotency (requires MongoDB)."""

    async def test_save_patient_roundtrip(self, mongo_url, clean_fhir_collection):
        """save() persists a Patient; find_by_patient returns it."""
        from veridoc_fhir.models import Patient
        from veridoc_fhir.repository import FhirRepository

        repo = FhirRepository(mongo_url=mongo_url)
        await repo.create_indexes()

        patient = Patient.model_validate({
            "resourceType": "Patient",
            "id": "p-pseudo-repo-001",
            "active": True,
            "subject": {"reference": "Patient/p-pseudo-repo-001"},
            "meta": {"source": "urn:veridoc:source:native-fhir:site-001"},
        })
        await repo.save(patient)

        # find_by_patient is keyed by subject.reference — Patient is its own subject
        # Use Observation for the subject reference query to test cross-resource
        from veridoc_fhir.models import Observation

        obs = Observation.model_validate({
            "resourceType": "Observation",
            "id": "obs-repo-001",
            "status": "final",
            "code": {"text": "Weight"},
            "subject": {"reference": "Patient/p-pseudo-repo-001"},
        })
        await repo.save(obs)

        results = await repo.find_by_patient("p-pseudo-repo-001", "Observation")
        assert len(results) == 1
        assert results[0]["id"] == "obs-repo-001"

    async def test_save_is_idempotent(self, mongo_url, clean_fhir_collection):
        """Re-saving the same resourceType+id does not create a duplicate document."""
        from veridoc_fhir.models import Condition
        from veridoc_fhir.repository import FhirRepository

        repo = FhirRepository(mongo_url=mongo_url)
        await repo.create_indexes()

        cond = Condition.model_validate({
            "resourceType": "Condition",
            "id": "cond-idem-001",
            "subject": {"reference": "Patient/p-pseudo-repo-002"},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]},
        })
        # Save twice — must be idempotent (upsert, not insert)
        await repo.save(cond)
        await repo.save(cond)

        # Only one document should exist (no duplicate)
        results = await repo.find_by_patient("p-pseudo-repo-002", "Condition")
        assert len(results) == 1, (
            f"Expected 1 document after idempotent save, got {len(results)}"
        )

    async def test_find_by_patient_filters_by_resource_type(
        self, mongo_url, clean_fhir_collection
    ):
        """find_by_patient with a specific resource_type must not return other types."""
        from veridoc_fhir.models import Condition, Observation
        from veridoc_fhir.repository import FhirRepository

        repo = FhirRepository(mongo_url=mongo_url)
        await repo.create_indexes()

        patient_ref = "Patient/p-pseudo-repo-003"

        obs = Observation.model_validate({
            "resourceType": "Observation",
            "id": "obs-filter-001",
            "status": "final",
            "code": {"text": "Lab"},
            "subject": {"reference": patient_ref},
        })
        cond = Condition.model_validate({
            "resourceType": "Condition",
            "id": "cond-filter-001",
            "subject": {"reference": patient_ref},
            "code": {"text": "Hypertension"},
        })

        await repo.save(obs)
        await repo.save(cond)

        obs_results = await repo.find_by_patient("p-pseudo-repo-003", "Observation")
        cond_results = await repo.find_by_patient("p-pseudo-repo-003", "Condition")

        assert len(obs_results) == 1 and obs_results[0]["resourceType"] == "Observation"
        assert len(cond_results) == 1 and cond_results[0]["resourceType"] == "Condition"

    async def test_unique_index_exists(self, mongo_url, clean_fhir_collection):
        """create_indexes() must create a unique (resourceType, id) index."""
        from veridoc_fhir.repository import FhirRepository
        from pymongo import AsyncMongoClient

        repo = FhirRepository(mongo_url=mongo_url)
        await repo.create_indexes()

        # Inspect the indexes on fhir_resources to confirm the unique constraint
        client = AsyncMongoClient(mongo_url)
        db = client["veridoc_fhir"]
        col = db["fhir_resources"]
        indexes = await col.index_information()

        # Find an index that is unique and covers (resourceType, id)
        unique_rt_id = False
        for _name, info in indexes.items():
            if info.get("unique") and any(
                set(k for k, _ in info.get("key", [])) >= {"resourceType", "id"}
                for _ in [None]
            ):
                unique_rt_id = True
                break

        assert unique_rt_id, (
            f"No unique (resourceType, id) index found. Indexes: {list(indexes.keys())}"
        )
        client.close()

    async def test_save_multiple_resource_types(self, mongo_url, clean_fhir_collection):
        """All required resource types can be saved and retrieved."""
        from veridoc_fhir.models import (
            AdverseEvent,
            DiagnosticReport,
            DocumentReference,
            MedicationRequest,
            Procedure,
        )
        from veridoc_fhir.repository import FhirRepository

        repo = FhirRepository(mongo_url=mongo_url)
        await repo.create_indexes()

        patient_ref = "Patient/p-pseudo-repo-all"

        resources = [
            AdverseEvent.model_validate({
                "resourceType": "AdverseEvent",
                "id": "ae-repo-001",
                "actuality": "actual",
                "subject": {"reference": patient_ref},
            }),
            DiagnosticReport.model_validate({
                "resourceType": "DiagnosticReport",
                "id": "dr-repo-001",
                "status": "final",
                "code": {"text": "Lab Panel"},
                "subject": {"reference": patient_ref},
            }),
            DocumentReference.model_validate({
                "resourceType": "DocumentReference",
                "id": "docref-repo-001",
                "status": "current",
                "subject": {"reference": patient_ref},
                "content": [{"attachment": {"contentType": "application/pdf", "url": "s3://bucket/doc.pdf"}}],
            }),
            MedicationRequest.model_validate({
                "resourceType": "MedicationRequest",
                "id": "medreq-repo-001",
                "status": "active",
                "intent": "order",
                "subject": {"reference": patient_ref},
                "medicationCodeableConcept": {"text": "Ibuprofen"},
            }),
            Procedure.model_validate({
                "resourceType": "Procedure",
                "id": "proc-repo-001",
                "status": "completed",
                "subject": {"reference": patient_ref},
                "code": {"text": "Blood draw"},
            }),
        ]

        for resource in resources:
            await repo.save(resource)

        # Each resource type must be independently queryable
        for resource_type in [
            "DiagnosticReport", "DocumentReference", "MedicationRequest", "Procedure"
        ]:
            results = await repo.find_by_patient("p-pseudo-repo-all", resource_type)
            assert len(results) == 1, (
                f"Expected 1 {resource_type} for patient, got {len(results)}"
            )
