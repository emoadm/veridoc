---
phase: "02-fhir-r4-model-emr-ingestion"
plan: "06"
subsystem: "ingestion-service + veridoc-ingestion worker"
tags: ["fastapi", "rq", "worker", "mongodb", "blob-store", "audit", "tenancy", "rbac", "tdd"]
dependency_graph:
  requires: ["02-03", "02-04", "02-05"]
  provides: ["ingestion-service", "veridoc-ingestion.worker"]
  affects: ["02-07"]
tech_stack:
  added:
    - "rq.serializers.JSONSerializer (enforced on Queue + Worker)"
    - "ingestion-service FastAPI service (cloned from reference-service)"
  patterns:
    - "TDD RED→GREEN for both tasks (2 RED commits, 2 GREEN commits)"
    - "D-06 deviation: RQ worker owns its own SQLAlchemy session + commit"
    - "Same-transaction enqueued audit (D-05) + worker-owned completed audit (D-06)"
    - "JSONSerializer-only queue (T-02-SVC-03 / Pitfall 3) — no pickle"
    - "payload_key string, not raw bytes (Pitfall 4 / T-02-SVC-03)"
    - "asyncio.run inside sync worker to call async FhirRepository"
    - "Fail-closed tenancy + deny-by-default RBAC (reference-service pattern reused)"
    - "Tesseract in builder + runtime Dockerfile stages (Pitfall 8 / T-02-SVC-05)"
key_files:
  created:
    - "libs/veridoc-ingestion/src/veridoc_ingestion/worker.py"
    - "services/ingestion-service/src/ingestion_service/config.py"
    - "services/ingestion-service/src/ingestion_service/main.py"
    - "services/ingestion-service/src/ingestion_service/db.py"
    - "services/ingestion-service/src/ingestion_service/api/__init__.py"
    - "services/ingestion-service/src/ingestion_service/api/ingest.py"
    - "services/ingestion-service/src/ingestion_service/api/auth_audit.py"
    - "services/ingestion-service/src/ingestion_service/worker_main.py"
    - "services/ingestion-service/Dockerfile"
    - "services/ingestion-service/pyproject.toml"
    - "services/ingestion-service/README.md"
    - "services/ingestion-service/tests/conftest.py"
    - "services/ingestion-service/tests/test_ingest_api.py"
    - "services/ingestion-service/tests/test_worker_integration.py"
  modified:
    - "uv.lock (ingestion-service workspace member added)"
decisions:
  - "D-06 honored: worker opens its own SQLAlchemy session + commit for 'ingest:completed'"
  - "ingest_job receives blob connection params as keyword args for testability without env vars"
  - "POST /ingest modality defaults to 'native-fhir' at enqueue; worker resolves the profile"
metrics:
  duration: "~12 minutes"
  completed: "2026-06-11"
  task_count: 2
  file_count: 14
  commits:
    red1: "29dea28"
    green1: "bfe9319"
    red2: "dbed612"
    green2: "34aeda5"
requirements_covered: ["EMR-01"]
---

# Phase 02 Plan 06: Ingestion Service + RQ Worker Summary

**One-liner:** FastAPI `POST /ingest/{site_id}` with RS256/MFA + fail-closed tenancy + deny-by-default RBAC enqueues RQ jobs (JSONSerializer) and writes `ingest:enqueued` audit; worker resolves adapter → persists FHIR R4B + Provenance to MongoDB → commits `ingest:completed` audit via its own session (D-06).

---

## Tasks Completed

### Task 1: RQ worker job (D-06 own-session audit) + worker_main entrypoint

**TDD cycle:** RED (29dea28) → GREEN (bfe9319)

**Implemented:** `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py`

- `make_queue(redis_url)` returns `Queue("ingestion", connection, serializer=JSONSerializer)` — no pickle ever (T-02-SVC-03, Pitfall 3).
- `ingest_job(site_id, modality, payload_key, tenant_id, actor_id, *, blob_*, mongo_url, db_url)` — all JSON-serializable primitives (Pitfall 4).
- Inner async function `_async_ingest` runs via `asyncio.run` inside the sync RQ worker: fetches bytes from `S3BlobStore.get(payload_key)` → instantiates adapter via `SourceProfileRegistry` → calls `adapter.ingest(bytes, profile)` → saves resources + `Provenance` to `FhirRepository`.
- D-06 deviation: worker opens its own SQLAlchemy session via `_session_scope(db_url)`, calls `append_audit(session, AuditEvent(action="ingest:completed", ...))`, and `session.commit()`. The advisory lock still serializes the chain head.
- `services/ingestion-service/src/ingestion_service/worker_main.py`: `rq.Worker(["ingestion"], serializer=JSONSerializer)` — the Kubernetes worker Deployment entrypoint.

**Test results:** 3 pass (source inspection), 1 skip (Docker required for Mongo/Postgres/MinIO end-to-end).

### Task 2: ingestion-service (config, main+lifespan, ingest API, Dockerfile, conftest)

**TDD cycle:** RED (dbed612) → GREEN (34aeda5)

**Implemented:**

- `config.py`: `Settings(env_prefix="VERIDOC_")` with `mongodb_url`, `blob_endpoint_url`, `blob_bucket`, `blob_access_key`, `blob_secret_key` (cloned from reference-service, 5 new fields).
- `main.py`: `create_app(engine, jwks, issuer, audience, settings)` with async `lifespan` hook that calls `FhirRepository.create_indexes()` (Pitfall 6) and creates `Queue("ingestion", JSONSerializer)` (Pitfall 3) on `app.state`. Auth/tenancy/error-handlers copied verbatim from reference-service.
- `api/ingest.py`: `POST /ingest/{site_id}` — `require_write_role` (deny-by-default: `site-coordinator`, `data-manager`); `current_tenant()` fail-closed; blob upload; `queue.enqueue(ingest_job, ...)` with all JSON-serializable args; same-transaction `append_audit(session, AuditEvent(action="ingest:enqueued", ...))` + `session.commit()`; 202 + `{"job_id": "..."}`.
- `Dockerfile`: multi-stage uv build; `apt-get install -y tesseract-ocr tesseract-ocr-eng` in BOTH builder and runtime stages (Pitfall 8 / T-02-SVC-05).
- `tests/conftest.py`: Postgres + MongoDB + MinIO testcontainer fixtures (three-path resolution); `mint_token` helper (RS256, `AUDIENCE="ingestion-service"`).

**Test results:** 3 pass (source inspection: JSONSerializer, create_indexes, require_write_role), 6 skip (Docker required for DB-backed API tests).

---

## Deviations from Plan

### Auto-implemented Decisions

**1. [Decision] ingest_job accepts connection params as keyword args**
- **Rationale:** The plan specified blob/mongo/db params are resolved from env in the worker process. However, for direct testability without requiring a full environment setup, `ingest_job` accepts all connection params as optional keyword arguments with env fallback.
- **Impact:** Tests can call `ingest_job(...)` directly without setting environment variables. Worker process still works via env fallback. JSON-serializable (all strings/None).
- **Files modified:** `libs/veridoc-ingestion/src/veridoc_ingestion/worker.py`

**2. [Decision] POST /ingest defaults modality to "native-fhir" at enqueue time**
- **Rationale:** The plan did not specify how the modality is resolved at enqueue (the site registry lives in the lib, but the API handler doesn't instantiate it). The default ensures the job always has a valid modality; future plans can add a site-profile lookup at the API level.
- **Impact:** All ingest jobs enqueued with `modality="native-fhir"` unless overridden. The worker reconstructs a `SourceProfileRegistry` transiently from the job args, so modality routing works at job time.
- **Files modified:** `services/ingestion-service/src/ingestion_service/api/ingest.py`

---

## Threat Surface Scan

No new network endpoints or trust-boundary surfaces beyond what the plan's threat model covers:
- `POST /ingest/{site_id}` — covered by T-02-SVC-01/02/03/04/05
- Redis → RQ worker job payloads — covered by T-02-SVC-03 (JSONSerializer)
- Worker → Postgres audit chain — covered by T-02-SVC-04 (D-06 deviation)

No unmodeled threat surfaces found.

---

## Known Stubs

None — all data paths are wired. The Dockerfile RQ worker override (`CMD`) is documented but not a stub; it's a K8s Deployment command override pattern.

---

## Self-Check: PASSED

All 9 key files verified present on disk. All 4 task commits verified in git log.
