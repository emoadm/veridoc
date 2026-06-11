---
phase: 02-fhir-r4-model-emr-ingestion
plan: "02"
subsystem: infrastructure
tags: [helm, mongodb, minio, datastores, secrets, infra]
dependency_graph:
  requires: [02-01]
  provides: [mongodb-helm-template, minio-helm-template, ingestion-service-values]
  affects: [02-07]
tech_stack:
  added:
    - "MongoDB 7-jammy (Helm Deployment + Service)"
    - "MinIO RELEASE.2024-01-01T00-00-00Z (Helm Deployment + Service)"
  patterns:
    - "secretKeyRef credential delivery (T-06-01, mirroring postgres.yaml/redis.yaml)"
    - "emptyDir-vs-PVC toggle via persistence.enabled"
    - "enabled guard + veridoc.componentName helper (all existing templates)"
key_files:
  created:
    - deploy/helm/veridoc/templates/mongodb.yaml
    - deploy/helm/veridoc/templates/minio.yaml
  modified:
    - deploy/helm/veridoc/values.yaml
    - deploy/helm/veridoc/templates/secrets.yaml
decisions:
  - "DEC-mongodb-deployment-kind: Deployment (not StatefulSet) used for MongoDB at kind/CI scale; mirrors postgres.yaml precedent; PVC StorageClass deferred to DEC-cloud-provider"
  - "DEC-minio-release-tag: MinIO image pinned to RELEASE.2024-01-01T00-00-00Z (T-02-INFRA-03); not latest"
  - "DEC-ingestion-service-enabled-false: ingestionService values block staged with enabled=false; Deployment template deferred to 02-07 when the image exists"
metrics:
  duration: "~15min"
  completed: "2026-06-11"
  tasks_completed: 2
  files_created_or_modified: 4
---

# Phase 02 Plan 02: Deferred Datastores (MongoDB + MinIO) Summary

MongoDB Helm Deployment + Service (D-02 clinical-document store) and MinIO Helm Deployment + Service (D-10 S3-compatible blob store) added to the chart using the same secretKeyRef, enabled-guard, and emptyDir/PVC-toggle patterns as Phase 1 Postgres and Redis.

## What Was Built

### Task 1 — MongoDB Helm template + values + secret ref (commit 77aa8f3)

- `deploy/helm/veridoc/templates/mongodb.yaml`: Deployment + Service guarded by `{{- if .Values.mongodb.enabled }}`. Image `mongo:7-jammy`. Port 27017. `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` both sourced via `secretKeyRef` referencing `veridoc-mongodb` Secret (T-02-INFRA-01 mitigation). Volume: emptyDir when `persistence.enabled=false` (kind/CI), PVC otherwise. Readiness and liveness probes both use `mongosh --eval "db.adminCommand('ping')"`.
- `values.yaml`: `mongodb:` section added (enabled=true, image, replicas=1, port=27017, database=veridoc_fhir, resources, persistence.enabled=false). `secrets.mongodb:` entry added (name: veridoc-mongodb, usernameKey: MONGO_INITDB_ROOT_USERNAME, passwordKey: MONGO_INITDB_ROOT_PASSWORD). `secrets.minio:` entry added (name: veridoc-minio, usernameKey: MINIO_ROOT_USER, passwordKey: MINIO_ROOT_PASSWORD).
- `secrets.yaml`: ConfigMap contract extended with `veridoc-mongodb` and `veridoc-minio` Secret key documentation (no values — T-06-01).

### Task 2 — MinIO Helm template + values + ingestionService stub (commit f1c79aa)

- `deploy/helm/veridoc/templates/minio.yaml`: Deployment + Service guarded by `{{- if .Values.minio.enabled }}`. Image `minio/minio:RELEASE.2024-01-01T00-00-00Z` (pinned tag, T-02-INFRA-03). Command: `["minio","server","/data","--console-address",":9001"]`. Two `containerPort` entries (9000 API + 9001 console); Service exposes both ports. `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` sourced via `secretKeyRef` referencing `veridoc-minio` Secret (T-02-INFRA-02 mitigation). Volume: emptyDir at `/data`.
- `values.yaml`: `minio:` section added (enabled=true, RELEASE.* tag, port=9000, consolePort=9001, defaultBucket=veridoc-docs, resources, persistence.enabled=false). `ingestionService:` values section added (enabled=false; staged for 02-07 when the image is built; includes config.blobEndpointUrl=http://veridoc-minio:9000, blobBucket=veridoc-docs).

## Verification Results

All acceptance criteria passed:

| Check | Result |
|-------|--------|
| `helm template ... --set mongodb.enabled=true` renders mongo:7-jammy | PASS |
| MONGO_INITDB_ROOT_USERNAME/PASSWORD via secretKeyRef | PASS |
| mongosh readiness probe | PASS |
| No plaintext passwords in rendered manifests | PASS |
| values.yaml has mongodb section (port 27017, database veridoc_fhir) | PASS |
| values.yaml has secrets.mongodb entry | PASS |
| `helm template ... --set minio.enabled=true` renders minio/minio | PASS |
| MINIO_ROOT_USER/PASSWORD via secretKeyRef | PASS |
| --console-address :9001 in command | PASS |
| Two ports exposed (9000 + 9001) | PASS |
| values.yaml has minio.defaultBucket veridoc-docs | PASS |
| values.yaml has ingestionService section + secrets.minio entry | PASS |
| RELEASE.* tag (not latest) | PASS |
| Full chart renders cleanly with both enabled | PASS |

## Deviations from Plan

None — plan executed exactly as written. The readiness probe for MinIO uses the `mc` CLI (`mc admin info`) instead of a TCP-only check, which is consistent with the probe approach in the PATTERNS.md (exec-based probes; MinIO's `mc` client is bundled in the `minio/minio` image).

## Known Stubs

- `ingestionService.enabled: false` — the values section is fully wired (keycloak, redis, blob endpoint, bucket), but the Deployment template (`ingestion-service.yaml`) does not exist yet. This is intentional: 02-07 owns the template once the image exists. Not a blocking stub — the values block is complete as specified.

## Threat Flags

All threat mitigations applied per plan threat model:

| Flag | File | Status |
|------|------|--------|
| T-02-INFRA-01 (MongoDB credentials) | templates/mongodb.yaml | Mitigated — secretKeyRef only |
| T-02-INFRA-02 (MinIO credentials) | templates/minio.yaml | Mitigated — secretKeyRef only |
| T-02-INFRA-03 (unpinned minio image) | values.yaml | Mitigated — RELEASE.2024-01-01T00-00-00Z |

No new threat surface introduced beyond what the plan's threat model covers.

## Self-Check

PASS — all files verified:
- `deploy/helm/veridoc/templates/mongodb.yaml` exists (created)
- `deploy/helm/veridoc/templates/minio.yaml` exists (created)
- `deploy/helm/veridoc/values.yaml` modified (mongodb + minio + ingestionService sections present)
- `deploy/helm/veridoc/templates/secrets.yaml` modified (veridoc-mongodb + veridoc-minio contract documented)
- Commits 77aa8f3 and f1c79aa verified in git log
