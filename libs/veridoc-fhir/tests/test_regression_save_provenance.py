"""Regression tests for CR-02 — FhirRepository.save() must persist id-less resources.

These tests use an in-memory async collection double (NO Docker / MongoDB) so they
run in-process and would have caught the CR-02 KeyError that the Docker-gated
integration tests skipped over.

CR-02: ``create_provenance`` produces a Provenance whose ``model_dump()`` has no
``id`` key (fhir.resources omits a None id). The previous ``save()`` indexed
``doc["id"]`` directly → ``KeyError: 'id'``, aborting every worker job after
clinical resources were persisted but before Provenance. ``save()`` must assign a
stable id and persist the document instead.
"""

from __future__ import annotations

import pytest


class _FakeUpdateResult:
    """Mimics pymongo's UpdateResult for replace_one(upsert=True)."""

    def __init__(self, upserted_id):
        self.upserted_id = upserted_id


class _FakeCollection:
    """Minimal in-memory async stand-in for an AsyncMongoClient collection.

    Records every replace_one call so tests can assert the persisted document and
    the upsert filter. No network, no Docker.
    """

    def __init__(self):
        self.calls: list[tuple[dict, dict]] = []
        self._store: dict[tuple, dict] = {}

    async def replace_one(self, filt, doc, upsert=False):
        self.calls.append((filt, doc))
        key = (filt.get("resourceType"), filt.get("id"))
        existed = key in self._store
        self._store[key] = doc
        # Simulate Mongo: upserted_id is set only on insert, None on replace.
        return _FakeUpdateResult(None if existed else f"_oid::{key[0]}::{key[1]}")


def _repo_with_fake_collection():
    """Build a FhirRepository whose _col is the in-memory fake (no Mongo client I/O)."""
    from veridoc_fhir.repository import FhirRepository

    repo = FhirRepository.__new__(FhirRepository)  # skip __init__ (no AsyncMongoClient)
    repo._col = _FakeCollection()
    return repo


@pytest.mark.anyio
async def test_save_provenance_without_id_does_not_raise():
    """A Provenance from create_provenance round-trips through save() (CR-02)."""
    from veridoc_fhir.provenance import create_provenance

    repo = _repo_with_fake_collection()

    prov = create_provenance(
        target_ref="Patient/p-pseudo-001",
        source="urn:veridoc:source:native-fhir:site-001",
        ingestion_path="native-fhir",
        actor_ref="Device/ingestion-service",
    )

    # Must NOT raise KeyError: 'id'
    returned_id = await repo.save(prov)

    assert returned_id, "save() must return a non-empty id for the Provenance"

    # The persisted document must carry an id and the correct resourceType,
    # and the upsert filter must be well-formed (no missing 'id').
    filt, doc = repo._col.calls[-1]
    assert filt["resourceType"] == "Provenance"
    assert filt["id"], "upsert filter must carry a non-empty id"
    assert doc["id"] == filt["id"], "persisted doc id must match the filter id"


@pytest.mark.anyio
async def test_save_assigns_id_when_dump_omits_it():
    """Even a hand-built id-less dump is saved with a generated id (defense in depth)."""

    class _IdLessResource:
        def model_dump(self):
            return {"resourceType": "Provenance"}  # no 'id' key at all

    repo = _repo_with_fake_collection()
    returned_id = await repo.save(_IdLessResource())

    assert returned_id, "save() must synthesize and return an id"
    filt, doc = repo._col.calls[-1]
    assert doc.get("id"), "save() must inject an id into the persisted document"
    assert filt["id"] == doc["id"]
