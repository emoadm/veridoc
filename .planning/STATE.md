---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: milestone
status: executing
stopped_at: Completed 01-05-PLAN.md.
last_updated: "2026-06-11T00:00:00.000Z"
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 6
  completed_plans: 5
  percent: 83
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

- **Current focus:** Phase 01 — platform-skeleton-audit-foundation

## Current Position

Phase: 01 (platform-skeleton-audit-foundation) — EXECUTING
Plan: 6 of 6 (next)

- **Phase:** 1 — Platform Skeleton & Audit Foundation (executing)
- **Plan:** 01-05 COMPLETE — reference-service wired end-to-end (D-07 walking skeleton): FastAPI POST/PUT /subjects flows HTTP → Keycloak-style JWT authn+MFA (veridoc-auth) → deny-by-default RBAC → fail-closed site/study tenancy (veridoc-tenancy) → deterministic pseudonym (veridoc-pseudonym) + AES-256-GCM envelope-encrypted PII (veridoc-crypto) → SAME-transaction hash-chained audit (veridoc-audit) → Postgres (atomic business+audit). Login attempts (success+failure) audited; GDPR Art.17 erasure × 21 CFR Part 11 immutability seam proven once (erase A → verify_chain still True, A undecryptable, B intact). Non-root secret-free Dockerfile for plan 06. PLAT-01/02/03 satisfied end-to-end. Next is 01-06 (CI + kind deploy).
- **Status:** Executing Phase 01
- **Progress:** Phase 0/8 complete; plans 5/6 in phase 01
  `[████████░░] 83%`

## Performance Metrics

- Phases complete: 0/8
- Plans complete: 5/6 (phase 01)
- Requirements mapped: 16/16 (100%)
- Orphaned requirements: 0

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | ~25min | 3 | 44 |
| 01 | 02 | ~40min | 2 | 18 |
| 01 | 03 | ~30min | 3 | 13 |
| 01 | 04 | ~25min | 3 | 18 |
| 01 | 05 | ~55min | 3 | 24 |

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

- **Last action:** Executed plan 01-05 (reference service wired end-to-end — D-07 walking
  skeleton). Task 1 (TDD RED→GREEN): config.py (pydantic-settings DB/Redis/Keycloak/KMS),
  db.py (SQLAlchemy 2.x engine + per-request session, handler-owned commit), models.py Subject
  (tenant_id, pseudonym_token, pii_ciphertext bytea), migrations/0001_subject.py + migrate.py
  (applies audit_log 0001 then subject), api/subjects.py (POST/PUT derive pseudonym +
  envelope-encrypt PII + insert/update from current_tenant() + append_audit in the SAME txn +
  commit once; Pydantic v2 extra=forbid; deny-by-default require_write_role), main.py
  create_app (async authn dependency: verify_token RS256+MFA + fail-closed tenancy bind;
  AuthError/ForbiddenError/TenancyError→401/403; open /healthz). Task 2 (TDD RED→GREEN):
  auth_audit.py (login-success/login-failure auditing wired into the authn dependency, each
  committed append-only) + create audit `after` carries base64 ciphertext; test_rbac (permitted
  2xx / cross-role 403 / cross-tenant denied / missing-MFA 401), test_login_audit (success+failure
  both audited), test_field_encryption (raw column ciphertext≠plaintext; decrypt round-trips),
  test_erasure_audit_immutability (erase A → verify_chain still True, A undecryptable, B intact);
  deploy/keycloak/test-users.json (6 users, 4 roles, 2 tenants, MFA). Task 3: non-root,
  secret-free multi-stage Dockerfile (uvicorn reference_service.main:app). 14 ref-service tests
  green vs local least-privilege Postgres; full repo 80 passed; clean-clone 59 passed/21 skipped;
  ruff clean. Commits b248bce, e3341d0, 95722a7, 7b1a5cc, 4f4cbec, e5bae2f. httpx recorded
  APPROVED before install (Encode, FastAPI test transport); fastapi/uvicorn/pydantic-settings
  installed (all APPROVED); no OIDC-glue package adopted. PLAT-01/02/03 proven end-to-end.

- **Next action:** Execute plan 01-06 (CI + kind deploy): build/load the reference-service
  Dockerfile, import veridoc-realm.json + test-users.json into a live Keycloak, run the DB- and
  Keycloak-backed tests in CI (Alembic env.py for both migrations), inject the client secret +
  KMS master key from K8s Secrets.

- **Stopped at:** Completed 01-05-PLAN.md.
- **Resume file:** None.
