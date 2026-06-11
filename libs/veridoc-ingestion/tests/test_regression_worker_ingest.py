"""Regression tests for the worker ingest core (CR-02 + CR-03).

These exercise ``worker._async_ingest`` end-to-end over a REAL Synthea fixture
bundle, using in-process fakes for the blob store and the FHIR repository (NO
Docker / MongoDB / Redis / S3). They would have caught:

- CR-03: ``resource.resource_type`` AttributeError on every saved resource
  (fhir.resources exposes ``get_resource_type()``, not ``resource_type``).
- CR-02: ``FhirRepository.save()`` KeyError on the id-less Provenance built for
  every batch.

The prior unit tests skipped the persistence path entirely (Docker-gated), so the
real fhir.resources runtime API and the Provenance save were never exercised
in-process.
"""

from __future__ import annotations

import pathlib

import pytest

_LIBS_DIR = pathlib.Path(__file__).parents[2]  # libs/
FHIR_FIXTURES = _LIBS_DIR / "veridoc-fhir" / "tests" / "fixtures" / "fhir"


class _FakeBlobStore:
    """Returns fixture bytes for any key; records nothing else."""

    def __init__(self, *, payload: bytes, **_kwargs):
        self._payload = payload

    def get(self, key: str) -> bytes:
        return self._payload

    def put(self, key: str, data: bytes, content_type: str) -> str:  # pragma: no cover
        return f"s3://fake/{key}"


class _FakeRepo:
    """In-memory FhirRepository double — persists resources to a list.

    Crucially it calls ``resource.get_resource_type()`` and ``resource.model_dump()``
    exactly as the real save path does, so CR-02/CR-03 regressions surface here.
    """

    instances: list["_FakeRepo"] = []

    def __init__(self, *, mongo_url: str = "", **_kwargs):
        self.saved: list[dict] = []
        self.closed = False
        _FakeRepo.instances.append(self)

    async def create_indexes(self) -> None:
        return None

    async def save(self, resource) -> str:
        # Mirror the real save() id handling (CR-02): model_dump may omit 'id'.
        doc = resource.model_dump()
        res_id = doc.get("id") or f"generated-{len(self.saved)}"
        doc["id"] = res_id
        self.saved.append(doc)
        return str(res_id)

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def _patched_worker(monkeypatch):
    """Patch the blob store + repository the worker imports, return the fake repo class."""
    import veridoc_ingestion.blob_store as blob_mod
    import veridoc_fhir.repository as repo_mod

    payload = next(FHIR_FIXTURES.glob("Corie618*.json")).read_bytes()

    def _blob_factory(**kwargs):
        return _FakeBlobStore(payload=payload, **kwargs)

    monkeypatch.setattr(blob_mod, "S3BlobStore", _blob_factory)
    monkeypatch.setattr(repo_mod, "FhirRepository", _FakeRepo)
    _FakeRepo.instances.clear()
    return _FakeRepo


@pytest.mark.anyio
async def test_async_ingest_reaches_persistence_native_fhir(_patched_worker):
    """worker._async_ingest over a Synthea bundle persists >0 resources, no Attr/KeyError."""
    from veridoc_ingestion.worker import _async_ingest

    result = await _async_ingest(
        site_id="site-001",
        modality="native-fhir",
        payload_key="site-001/abc.bin",
        tenant_id="site-001/study-A",
        actor_id="user-1",
        blob_endpoint_url=None,
        blob_bucket="veridoc-docs",
        blob_access_key="",
        blob_secret_key="",
        mongo_url="mongodb://unused",
    )

    # Persistence reached without AttributeError (CR-03) or KeyError (CR-02).
    assert result["resource_ids"], "must persist at least one resource id"
    assert result["provenance_id"], "must persist a Provenance id"

    repo = _patched_worker.instances[-1]
    assert len(repo.saved) > 1, "must persist clinical resources plus a Provenance"
    assert repo.closed, "WR-02: repo must be closed (finally) even on the success path"

    # A Provenance must be among the saved documents (proves the id-less save worked).
    saved_types = {d["resourceType"] for d in repo.saved}
    assert "Provenance" in saved_types, "Provenance must be persisted for the batch"
    assert "Patient" in saved_types, "Synthea bundle must persist a Patient"


@pytest.mark.anyio
async def test_async_ingest_unknown_modality_fails_closed(_patched_worker):
    """WR-03: an unrecognized modality raises (dead-letter), never default-routes."""
    from veridoc_ingestion.worker import _async_ingest

    with pytest.raises(ValueError):
        await _async_ingest(
            site_id="site-001",
            modality="totally-bogus-modality",
            payload_key="site-001/abc.bin",
            tenant_id="site-001/study-A",
            actor_id="user-1",
            blob_endpoint_url=None,
            blob_bucket="veridoc-docs",
            blob_access_key="",
            blob_secret_key="",
            mongo_url="mongodb://unused",
        )
