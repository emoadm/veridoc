"""FHIR R4B resource persistence to MongoDB (D-02).

Provides :class:`FhirRepository`, an async MongoDB repository built on pymongo's
``AsyncMongoClient`` (NOT motor — motor is deprecated as of 2026-05-14; Pitfall 2).

Design decisions
----------------
- **Single collection:** ``fhir_resources`` with ``resourceType`` indexed.
  Industry pattern from Smile CDR; avoids JOIN anti-pattern in MongoDB.
  The unique compound index ``(resourceType, id)`` enforces one logical resource
  per identity tuple; ``(resourceType, subject.reference)`` covers patient queries.

- **Upsert-only:** ``save()`` uses ``replace_one(..., upsert=True)`` — inserting a
  new document the first time and silently replacing it on repeat saves.
  This makes ingest pipelines idempotent: reprocessing a resource does not create
  duplicates (T-02-FHIR-01; Pitfall 6).

- **Startup index creation:** :meth:`create_indexes` MUST be called once at
  FastAPI ``lifespan`` startup, not per-request (Pitfall 6 — missing indexes cause
  full COLLSCAN queries on every patient lookup).

Security notes
--------------
- ``save()`` accepts only ``fhir.resources.R4B`` model instances, never raw dicts.
  The Pydantic v2 model has already validated the FHIR schema before save (T-02-FHIR-01).
- ``resourceType`` is taken from ``model_dump()``; it cannot be injected by a caller.

Analogue: ``services/reference-service/src/reference_service/db.py``
(session/engine factory + scope pattern, constructor-injects-client,
method-per-operation discipline).
"""

from __future__ import annotations

import uuid

from pymongo import AsyncMongoClient, IndexModel, ASCENDING

__all__ = ["FhirRepository"]


class FhirRepository:
    """Async FHIR resource persistence to MongoDB (D-02).

    Parameters
    ----------
    mongo_url:
        MongoDB connection URL (e.g. ``"mongodb://localhost:27017"``).
        Injected at construction time; follows the reference-service
        ``make_engine(database_url)`` dependency-injection pattern.
    db_name:
        MongoDB database name. Defaults to ``"veridoc_fhir"``.

    Usage::

        repo = FhirRepository(mongo_url=settings.mongodb_url)
        await repo.create_indexes()   # call once at FastAPI lifespan startup
        await repo.save(patient)
        rows = await repo.find_by_patient("p-pseudo-001", "Observation")
    """

    def __init__(self, mongo_url: str, db_name: str = "veridoc_fhir") -> None:
        # AsyncMongoClient — NOT motor (deprecated EOL 2026-05-14, Pitfall 2)
        self._client: AsyncMongoClient = AsyncMongoClient(mongo_url)
        self._db = self._client[db_name]
        # Single unified collection; resourceType field is indexed for every query path
        self._col = self._db["fhir_resources"]

    async def create_indexes(self) -> None:
        """Create compound indexes for common queries.

        Must be called **once at startup** (FastAPI lifespan hook) — not per request.
        Calling it multiple times is safe: pymongo silently ignores duplicate index
        declarations (``ensure_index`` semantics).

        Indexes created:
        - ``(resourceType, id)`` — unique; enforces idempotent upsert (T-02-FHIR-04).
          Identity in this single-collection design is the (resourceType, id) TUPLE,
          not a bare ``id``; the same ``id`` under different resource types is a
          distinct logical resource.
        - ``(resourceType, subject.reference)`` — patient resource lookup (SC-1)
        - ``(resourceType, meta.source)`` — provenance source query

        WR-08: the previous standalone non-unique ``id`` index is intentionally
        NOT created. No query path looks up by bare ``id`` (``save`` filters on the
        compound key and ``find_by_patient`` on subject.reference), so it was pure
        write overhead; it also implied a global-id-uniqueness contract that this
        design does not make (identity is the compound tuple). Dropping it keeps the
        index contract unambiguous.
        """
        await self._col.create_index(
            [("resourceType", ASCENDING), ("id", ASCENDING)],
            unique=True,
            name="ix_resourceType_id_unique",
        )
        await self._col.create_index(
            [("resourceType", ASCENDING), ("subject.reference", ASCENDING)],
            name="ix_resourceType_subject_ref",
        )
        await self._col.create_index(
            [("resourceType", ASCENDING), ("meta.source", ASCENDING)],
            name="ix_resourceType_meta_source",
        )

    async def save(self, resource) -> str:
        """Upsert a ``fhir.resources.R4B`` model instance into the collection.

        Parameters
        ----------
        resource:
            A validated ``fhir.resources.R4B`` resource model (Pydantic v2).
            Raw dicts are not accepted — the caller must validate first
            (T-02-FHIR-01: untrusted shape validation before storage).

        Returns
        -------
        str
            The MongoDB ``_id`` as a string (upserted or replaced document ID).
        """
        doc = resource.model_dump()
        # CR-02: fhir.resources omits ``id`` from model_dump() when it is None
        # (e.g. a Provenance built by create_provenance). Keying the upsert on
        # ``doc["id"]`` would then raise KeyError and abort the ingest job after
        # clinical resources were already persisted. Assign a stable UUID id when
        # absent and persist it, so every document is addressable and the upsert
        # filter is always well-formed.
        res_id = doc.get("id")
        if res_id is None:
            res_id = str(uuid.uuid4())
            doc["id"] = res_id
        # resourceType comes directly from model_dump() — cannot be injected
        result = await self._col.replace_one(
            {
                "resourceType": doc["resourceType"],
                "id": res_id,
            },
            doc,
            upsert=True,
        )
        return str(result.upserted_id or res_id)

    async def find_by_patient(
        self, patient_id: str, resource_type: str
    ) -> list[dict]:
        """Return all resources of ``resource_type`` referencing ``patient_id``.

        Queries the indexed ``(resourceType, subject.reference)`` compound path —
        never a full COLLSCAN (T-02-FHIR-04).

        Parameters
        ----------
        patient_id:
            The pseudonymized patient ID (without the ``Patient/`` prefix).
        resource_type:
            FHIR resource type string (e.g. ``"Observation"``, ``"Condition"``).

        Returns
        -------
        list[dict]
            Zero or more FHIR resource documents as plain dicts.
        """
        cursor = self._col.find({
            "resourceType": resource_type,
            "subject.reference": f"Patient/{patient_id}",
        })
        return await cursor.to_list(length=None)

    def close(self) -> None:
        """Close the underlying MongoDB client connection.

        Call in FastAPI lifespan ``yield`` teardown::

            yield
            repo.close()
        """
        self._client.close()
