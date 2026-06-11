---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: milestone
status: executing
stopped_at: 02-06 COMPLETE — advancing to 02-07
last_updated: "2026-06-11T20:45:00Z"
progress:
  total_phases: 8
  completed_phases: 1
  total_plans: 14
  completed_plans: 13
  percent: 85
---

# VeriDoc AI — Project State

Project memory. Updated as work progresses.

## Project Reference

- **Core value:** AI-powered SDV — a fleet of specialized agents verifies EMR source
  data against Medidata Rave eCRF data, with ALCOA+ assessment, prioritized
  discrepancy queries, and a tamper-evident audit trail. Decision-support only
  (mandatory human-in-the-loop).

- **Current milestone:** Milestone 1 — Buildable Phase-1 Core.
- **Milestone success metric:** Synthetic FHIR R4 + Rave mock in → prioritized
  discrepancy queries + ALCOA+ assessment + complete tamper-evident audit trail out,
  verifiable end-to-end against fixtures.

- **Current focus:** Phase 02 — fhir-r4-model-emr-ingestion

## Current Position

Phase: 02 (fhir-r4-model-emr-ingestion) — EXECUTING
Plan: 7 of 7

- **Phase:** 1 — Platform Skeleton & Audit Foundation (COMPLETE)
- **Plan:** 02-01 COMPLETE — Wave 0 foundation: veridoc-fhir + veridoc-ingestion libs registered,
  all 9 Phase 02 packages installed, Synthea R4B fixtures + AdverseEvent + HL7/PDF/image fixtures
  committed, Mongo/MinIO testcontainer conftests wired.

- **Plan:** 02-02 COMPLETE — Deferred datastores: MongoDB + MinIO Helm templates + values + secret refs
  (D-02/D-10). mongodb.yaml + minio.yaml + ingestionService values staged for 02-07.

- **Plan:** 02-03 COMPLETE — veridoc-fhir R4B model layer: models.py, repository.py,
  provenance.py, extensions.py (FHIR R4B resource re-exports + MongoDB FhirRepository + Provenance factory).

- **Plan:** 02-04 COMPLETE — veridoc-ingestion contracts: SourceAdapter ABC, SourceProfile,
  SourceProfileRegistry, OcrEngine ABCs (Tesseract/Textract/Azure stubs), BlobStore ABCs
  (S3/Azure stubs), ProprietaryAdapter stub.

- **Plan:** 02-05 COMPLETE — EMR ingestion adapters (D-11): NativeFhirAdapter, HL7v2Adapter
  + explicit hl7v2_fhir mapping layer (D-12), PdfExcelAdapter (pypdf/openpyxl), OcrAdapter
  (DocumentReference + ALCOA flags), RuleBasedExtractor (D-09). All four registered in
  SourceProfileRegistry. PII pseudonymized at ingestion (D-14, SC-4). 9/10 adapter tests pass.

- **Plan:** 02-06 COMPLETE — ingestion-service FastAPI + RQ worker (D-04/D-06):
  POST /ingest/{site_id} (RS256/MFA + fail-closed tenancy + deny-by-default RBAC →
  blob store upload → RQ enqueue with JSONSerializer → 202 + job_id + same-txn
  "ingest:enqueued" audit). Worker: blob.get → adapter.ingest → FhirRepository.save
  + Provenance → worker-owned "ingest:completed" audit commit (D-06). Dockerfile with
  tesseract-ocr in builder + runtime (Pitfall 8). Commits: 29dea28/bfe9319/dbed612/34aeda5.

- **Status:** Executing Phase 02 (Plans 1-6 of 7 COMPLETE, advancing to Plan 7)
- **Progress:** [█████████░] 85%

## Performance Metrics

- Phases complete: 1/8
- Plans complete: 13/14 (6 phase 01 + 6 phase 02 + plan 02-07 remaining)
- Requirements mapped: 16/16 (100%)
- Orphaned requirements: 0

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | ~25min | 3 | 44 |
| 01 | 02 | ~40min | 2 | 18 |
| 01 | 03 | ~30min | 3 | 13 |
| 01 | 04 | ~25min | 3 | 18 |
| 01 | 05 | ~55min | 3 | 24 |
| 02 | 01 | ~25min | 3 | 22 |
| 02 | 02 | ~15min | 2 | 4 |
| 02 | 05 | ~45min | 2 | 9 |
| 02 | 06 | ~12min | 2 | 14 |

## Accumulated Context

### Locked decisions

- DEC-fhir-r4-canonical — FHIR R4 is the canonical internal patient model.
- DEC-rave-primary-ecrf — Medidata Rave (MDRWS) is the primary eCRF.
- DEC-human-in-the-loop — mandatory human review for ALL clinical decisions; binding
  architectural constraint.

- DEC-gamp5-csv — GAMP 5 CSV lifecycle; validation-ready docs throughout; IQ/OQ/PQ
  gates *commercial* deployment.

- DEC-regional-data-residency — regional cloud residency designed in from day one.

- DEC-monorepo-tooling (01-01) — uv (Python) + pnpm (JS/TS) workspaces glued by go-task
  (Taskfile); NOT Nx/Turborepo (D-08). uv chosen over Poetry; go-task over Make.

- DEC-supply-chain-gate (01-01) — every third-party install gated by committed
  docs/validation/PACKAGE-LEGITIMACY.md; lockfiles + .tool-versions pinned (T-01-SC/01).

- DEC-rfc8785-authentic (01-01) — rfc8785 adjudicated authentic (Trail of Bits); install
  the package in plan 01-02, no in-house JCS fallback.

- DEC-audit-hash-chain (01-02) — audit chain = SHA-256(prev_hash || rfc8785-JCS(payload)),
  genesis prev_hash = ""; deterministic hash payload excludes server columns and normalizes
  occurred_at to UTC microsecond ISO (single _payload helper) so persisted rows re-hash exactly.

- DEC-audit-same-txn-writer (01-02) — append_audit joins the caller's Session, takes
  pg_advisory_xact_lock to serialize the chain head (no fork), and NEVER commits (D-05);
  append-only enforced by a BEFORE UPDATE OR DELETE trigger + INSERT/SELECT-only grant.
  audit_log carries nullable agent_decision/agent_confidence now (D-06).

- DEC-kms-tink-hkdf (01-03) — Google Tink (tink-hkdf) backs the KMS abstraction;
  aws-encryption-sdk NOT installed for veridoc-crypto. Master key + per-patient HKDF-derived
  key hierarchy; a GLOBAL pseudonym/encryption key is EXPLICITLY REJECTED (Pitfall 3, A7).
  Field encryption = AES-256-GCM envelope (per-field DEK wrapped by the per-patient key via
  Tink AEAD; patient_id as AAD; NOT pgcrypto). Pseudonym = HMAC-SHA256 over the SAME
  per-patient key (D-12, no re-identification table). Erasure = delete the patient's HKDF
  derivation material (crypto-shred) → ciphertext undecryptable + token irrecomputable,
  others intact, audit trail preserved (GDPR Art. 17). KEY-HIERARCHY.md records it (A7 resolved).

- DEC-auth-direct-jwt (01-04) — veridoc-auth verifies Keycloak JWTs DIRECTLY with the
  already-APPROVED pyjwt[crypto] + jwcrypto; NO OIDC-glue package (fastapi-keycloak-middleware/
  authlib) adopted. `cryptography` (PyCA) recorded APPROVED in PACKAGE-LEGITIMACY.md before
  install (authentic required transitive dep). RS256 pinned (rejects alg=none + HS256); iss/aud/
  exp verified; MFA enforced in the API tier (acr=mfa OR amr otp), defence-in-depth over the
  realm's REQUIRED OTP flow. RBAC is deny-by-default across the 8 realm roles (403 on miss);
  IP-allowlist is a data-driven per-tenant hook (allow when unset).

- DEC-tenancy-fail-closed (01-04) — request-scoped Tenant(site, study) lives in a contextvar
  with NO default; current_tenant() and tenant_from_claims RAISE TenancyError when unset/missing
  (fail-closed, never run unscoped — D-03, T-04-04). contextvars give per-asyncio-task isolation
  (no cross-request leak). tenancy_middleware sources the tenant from the auth Principal's claims.

- DEC-keycloak-realm-as-code (01-04) — the 8 roles + browser-mfa REQUIRED OTP flow + acr.loa.map +
  confidential reference-service OIDC client (audience + realm-role + site/study mappers) +
  session timeouts are committed as deploy/keycloak/veridoc-realm.json (--import-realm; Pitfall 4
  closed). No plaintext secrets — client secret is a placeholder resolved from a K8s Secret at
  deploy (01-06). RBAC-MATRIX.md is the 8-role permission-matrix validation evidence.

- DEC-pymongo-asyncclient (02-01) — Use pymongo AsyncMongoClient for MongoDB; motor is EOL
  2026-05-14. motor explicitly excluded from uv.lock (T-02-01). APPROVED in PACKAGE-LEGITIMACY.md.

- DEC-fhir-r4b-subpackage (02-01) — Always import via `fhir.resources.R4B.*`; top-level
  `fhir.resources.*` resolves to R5 since v7.0.0. All 9 resource types in scope (Patient,
  Encounter, Observation, Condition, MedicationRequest, AdverseEvent, DiagnosticReport,
  DocumentReference, Procedure) use the R4B sub-package.

- DEC-synthea-seed42 (02-01) — Synthea fixtures use `-s 42 --exporter.fhir.use_us_core_ig=false`
  for reproducible R4B bundles. Pitfall 7: US Core IG disabled; R4B-strict-only validation.
  5 Synthea bundles + hand-crafted AdverseEvent (gap A7) committed as test fixtures.

- DEC-rq-json-serializer (02-01) — RQ job queue uses JSONSerializer; pickle explicitly excluded
  (RCE risk). All `ingest_job` arguments must be JSON-serializable primitives (no raw bytes).

- DEC-mongodb-deployment-kind (02-02) — Deployment (not StatefulSet) for MongoDB at kind/CI
  scale, mirroring postgres.yaml. PVC StorageClass deferred to DEC-cloud-provider resolution.

- DEC-minio-release-tag (02-02) — MinIO image pinned to RELEASE.2024-01-01T00-00-00Z
  (T-02-INFRA-03); never use `latest`. Update via values overlay in prod environments.

- DEC-ingestion-service-enabled-false (02-02) — ingestionService values section staged with
  enabled=false; Deployment template (ingestion-service.yaml) deferred to 02-07 when the
  ingestion-service Docker image exists.

- DEC-hl7v2-natural-id-cx1 (02-05) — PID.3 CX_1 (raw ID component only) used as natural_id
  for pseudonym_token; assigning authority stripped (open question #3 from RESEARCH.md resolved).
  Rationale: authority is site metadata, not patient identity; CX_1 is the stable patient ID.

- DEC-native-fhir-9-resources (02-05) — NativeFhirAdapter filters Synthea bundles to 9 scoped
  resource types only (Patient, Encounter, Observation, Condition, MedicationRequest, AdverseEvent,
  DiagnosticReport, DocumentReference, Procedure, Provenance). Claim/EOB/Immunization excluded.

- DEC-ocr-docstatus-preliminary (02-05) — OcrAdapter sets DocumentReference.docStatus=preliminary
  at ingestion time (open question #2 from RESEARCH.md resolved). Phase 5 ALCOA+ agent updates
  to final or escalates.

### Open decisions

- DEC-cloud-provider — AWS vs Azure UNDECIDED. Keep IaC provider-portable until decided.

### Parallel constraints (track, do not block phases)

- CON-regulatory-strategy-first — RA strategy + CSV plan (runs in parallel).
- CON-medidata-partner — production Rave access gated on partner status; this
  milestone uses a Rave **mock** behind an abstraction layer.

- CON-iq-oq-pq-validation / CON-gamp5-csv — PQ + production access gate COMMERCIAL
  deployment, not build start.

- CON-pilot-partner — pilot CRO/Sponsor engagement (business prerequisite, non-blocking).

### Binding standards

- Coding: SNOMED CT, MedDRA, LOINC, CTCAE v5.0, ATC/WHO Drug Dictionary.
- Audit trail: immutable, 15-year retention, captures agent decisions + confidence.
- Security: 21 CFR Part 11 / Annex 11 / GDPR / HIPAA baseline from day one.

### Todos / watch items

- Phase 3 (Rave) and Phase 2 (EMR) both depend only on Phase 1 — can be planned in
  either order; Phase 4 needs both.

- Build Rave abstraction layer cleanly so mock → production swap is trivial when
  CON-medidata-partner clears.

### Blockers

- None.

## Session Continuity

- **Last action:** Completed 02-06-PLAN.md — ingestion-service FastAPI + RQ worker end-to-end
  (D-04/D-06): POST /ingest/{site_id} (RS256/MFA + fail-closed tenancy + deny-by-default RBAC
  → blob upload → RQ enqueue JSONSerializer → 202 + same-txn "ingest:enqueued" audit). Worker:
  blob.get → adapter.ingest → FhirRepository.save + Provenance → worker-owned "ingest:completed"
  audit (D-06). Dockerfile with tesseract-ocr (Pitfall 8 closed). TDD RED→GREEN for both tasks.
  Commits: 29dea28 (RED-1), bfe9319 (GREEN-1), dbed612 (RED-2), 34aeda5 (GREEN-2).
  SUMMARY at .planning/phases/02-fhir-r4-model-emr-ingestion/02-06-SUMMARY.md.

- **Next action:** Plan 02-07 — Phase 02 wrap-up: Helm ingestion-service.yaml Deployment,
  CI smoke test, integration validation, Phase 02 close.

- **Stopped at:** 02-06 COMPLETE — advancing to 02-07
- **Resume file:** .planning/phases/02-fhir-r4-model-emr-ingestion/02-07-PLAN.md
