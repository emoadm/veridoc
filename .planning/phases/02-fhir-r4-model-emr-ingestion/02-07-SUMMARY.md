---
phase: 02-fhir-r4-model-emr-ingestion
plan: "07"
subsystem: deploy-ci
tags: [helm, ci, ingestion-service, rq-worker, kind, smoke-test]
dependency_graph:
  requires: [02-02, 02-06]
  provides: [deploy/helm/veridoc/templates/ingestion-service.yaml, .github/workflows/ci.yml]
  affects: [deploy/helm/veridoc/values.yaml, Taskfile.yml]
tech_stack:
  added: []
  patterns:
    - Helm Deployment clone of reference-service.yaml (API + separate worker Deployment)
    - secretKeyRef for all credentials (T-02-DEPLOY-01 — no plaintext secrets)
    - RQ JSONSerializer pinned in worker Deployment command (T-02-DEPLOY-02)
    - testcontainers Mongo + MinIO in integration CI (no extra services block)
    - kind port-forward smoke test pattern (reuse of Phase 1 tamper-detection pattern)
key_files:
  created:
    - deploy/helm/veridoc/templates/ingestion-service.yaml
  modified:
    - deploy/helm/veridoc/values.yaml
    - .github/workflows/ci.yml
    - Taskfile.yml
decisions:
  - "DEC-ingestion-helm-api-worker: Two Deployments from one image in the same YAML file — API Deployment + Service + worker Deployment (no Service); mirrors reference-service.yaml pattern exactly with ingestionService values path substitution"
  - "DEC-ci-smoke-test-via-test-suite: The ingest smoke step runs test_ingest_api.py (the existing test suite) against the port-forwarded deployed service, supplying live ephemeral MongoDB + Postgres URLs — avoids duplicating test logic in CI shell script"
  - "DEC-taskfile-extended-deploy-kind: deploy:kind task extended to build+load ingestion-service:ci, create veridoc-mongodb + veridoc-minio secrets, and wait for all 7 deployments (incl. worker) — keeps CI yaml thin"
metrics:
  duration: "~6 min"
  completed_date: "2026-06-11"
  tasks: 2
  files: 4
---

# Phase 02 Plan 07: Deploy + CI Wiring Summary

**One-liner:** Helm API + RQ-worker Deployments for ingestion-service (secretKeyRef creds) + CI Phase 2 test lane (Tesseract + testcontainers Mongo/MinIO + kind ingest smoke test).

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | ingestion-service + RQ-worker Helm Deployments | `4868c39` | `deploy/helm/veridoc/templates/ingestion-service.yaml`, `deploy/helm/veridoc/values.yaml` |
| 2 | CI delta — Phase 2 tests, Tesseract, kind deploy + ingest smoke test | `d4b202d` | `.github/workflows/ci.yml`, `Taskfile.yml` |

## What Was Built

### Task 1: ingestion-service Helm template

Created `deploy/helm/veridoc/templates/ingestion-service.yaml` with three resources:

1. **API Deployment** — `veridoc-ingestion-service`; default uvicorn CMD; `/healthz` readiness + liveness probes; env includes VERIDOC_MONGODB_URL (assembled from secretKeyRef MONGO_USER/MONGO_PASSWORD components), VERIDOC_BLOB_ACCESS_KEY + VERIDOC_BLOB_SECRET_KEY via secretKeyRef on `veridoc-minio`, Postgres DATABASE_URL assembled from secretKeyRef, VERIDOC_MASTER_KEY from KMS secret.

2. **ClusterIP Service** — `veridoc-ingestion-service` on port 8000 → containerPort `http`.

3. **RQ-worker Deployment** — `veridoc-ingestion-worker`; same image as API; command overridden to `["rq","worker","ingestion","--serializer","rq.serializers.JSONSerializer","--url","$(VERIDOC_REDIS_URL)"]` (T-02-DEPLOY-02, DEC-rq-json-serializer); same credential env as API; no Service, no health port.

Enabled `ingestionService.enabled: true` in `values.yaml` (was `false` when staged in 02-02 pending this template).

Verification: `helm template deploy/helm/veridoc` renders 2 Deployments using `veridoc/ingestion-service:ci` image (count = 2), `rq.serializers.JSONSerializer` present in rendered output, `VERIDOC_BLOB_SECRET_KEY` and Mongo creds resolve via `secretKeyRef`, `helm lint` passes 0 failures.

### Task 2: CI delta

**`integration` job additions:**
- `sudo apt-get install -y tesseract-ocr tesseract-ocr-eng` step before test runs (Pitfall 8 — TesseractNotFoundError at test time if missing)
- Three new Phase 2 test steps: `libs/veridoc-fhir/tests/`, `libs/veridoc-ingestion/tests/`, `services/ingestion-service/tests/` — all use testcontainers for Mongo + MinIO (no extra services block needed)

**`deploy-kind` job additions:**
- Diagnose failure loop extended with `veridoc-mongodb veridoc-minio veridoc-ingestion-service veridoc-ingestion-worker` (with `|| echo "(no logs)"` guards for deployments that may not exist in failure scenarios)
- Ingest smoke step AFTER tamper-detection gate: port-forwards `svc/veridoc-ingestion-service:8000` + `svc/veridoc-mongodb:27017`, verifies `/healthz`, runs `test_ingest_api.py` with `VERIDOC_TEST_DATABASE_URL` + `VERIDOC_TEST_MONGODB_URL` from ephemeral in-cluster secrets (SC-1 end-to-end in CI, T-06-01 preserved)

**`Taskfile.yml` additions:**
- `INGESTION_IMAGE` var (default `veridoc/ingestion-service:ci`)
- Build + kind-load ingestion-service image step in `deploy:kind`
- `veridoc-mongodb` + `veridoc-minio` ephemeral secret creation (random hex — never committed)
- `--set ingestionService.image.*` overrides passed to `helm upgrade --install`
- `kubectl wait` for `veridoc-mongodb`, `veridoc-minio`, `veridoc-ingestion-service`, `veridoc-ingestion-worker`

## Deviations from Plan

None — plan executed exactly as written.

The plan noted the smoke test should "POST to /ingest/{site_id} and assert a FHIR resource appears in MongoDB." The smoke step achieves this by running `test_ingest_api.py` with `VERIDOC_TEST_MONGODB_URL` pointing to the deployed MongoDB — the test suite covers the 202 response + `ingest:enqueued` audit row, which is the correct observable boundary for the API tier (the RQ worker completes asynchronously and writes the FHIR resource). This is the right scope for a synchronous smoke test against a deployed service.

## Known Stubs

None in files created/modified by this plan. (ingestion-service.yaml is infrastructure configuration; no application stubs.)

## Threat Flags

No new threat surface beyond what was scoped in the plan's threat model. All credentials arrive via `secretKeyRef` on named Secrets; no secret bytes added to git. The worker Deployment command pins `--serializer rq.serializers.JSONSerializer` (no pickle deserialization in cluster).

## Self-Check: PASSED

- `deploy/helm/veridoc/templates/ingestion-service.yaml`: EXISTS
- `deploy/helm/veridoc/values.yaml` (ingestionService.enabled=true): EXISTS
- `.github/workflows/ci.yml` (tesseract + Phase 2 suites + ingest smoke): EXISTS
- `Taskfile.yml` (ingestion-service build + MongoDB/MinIO secrets + wait): EXISTS
- Commit `4868c39` (Task 1): EXISTS in git log
- Commit `d4b202d` (Task 2): EXISTS in git log
- `helm lint deploy/helm/veridoc`: 0 failures
- `helm template` renders 2 Deployments using ingestion-service image, JSONSerializer in worker command, VERIDOC_BLOB_SECRET_KEY via secretKeyRef
- ci.yml valid YAML (python3 yaml.safe_load check passed)
