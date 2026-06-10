---
phase: 01-platform-skeleton-audit-foundation
plan: 05
subsystem: reference-service
tags: [fastapi, walking-skeleton, d-07, oidc, mfa, rbac, tenancy, envelope-encryption, pseudonym, same-txn-audit, crypto-shred, gdpr-art17, 21cfr-part11, dockerfile, plat-01, plat-02, plat-03]

# Dependency graph
requires:
  - 01-01 uv workspace member services/reference-service + APPROVED package gate
  - 01-02 veridoc_audit (append_audit same-txn, verify_chain, AuditEvent, audit_log migration)
  - 01-03 veridoc_crypto (encrypt_field/decrypt_field/erase_patient) + veridoc_pseudonym (pseudonym_token)
  - 01-04 veridoc_auth (verify_token RS256+MFA, require_role/check_roles, Principal) + veridoc_tenancy (current_tenant fail-closed, tenant_from_claims) + Keycloak realm-as-code
provides:
  - "reference_service.create_app(engine, jwks, issuer, audience) -> FastAPI (the D-07 walking-skeleton service)"
  - "POST /subjects + PUT /subjects/{id} — authn(MFA) -> RBAC -> fail-closed tenancy -> pseudonym + envelope-encrypt -> same-transaction hash-chained audit -> Postgres"
  - "GET /healthz — open liveness probe (no auth)"
  - "login-attempt auditing (login-success / login-failure) at the service edge (Part 11 access log)"
  - "migrations/0001_subject.py (subject table) + reference_service.migrate (applies audit_log 0001 then subject)"
  - "services/reference-service/Dockerfile (non-root, secret-free, uvicorn entrypoint) for plan 06 CI/kind"
  - "deploy/keycloak/test-users.json (6 users, 4 roles, 2 tenants, MFA-enabled)"
affects: [01-06-ci-kind-deploy]

# Tech tracking
tech-stack:
  added: [fastapi 0.136.3, uvicorn 0.49.0, "pydantic-settings 2.14.1", httpx 0.28.1, starlette 1.2.1]
  patterns:
    - "D-07 walking skeleton: ONE service wires all five shared libs end-to-end; Phases 2-7 clone this exact path"
    - "Same-transaction audited business write (D-05): handler INSERTs the Subject + calls append_audit on the SAME session, commits ONCE -> business row + hash-chained audit row are atomic"
    - "The deterministic pseudonym token doubles as the crypto patient_id at rest, so a single crypto-shred (erase_patient(token)) makes BOTH ciphertext undecryptable AND token irrecomputable without storing the natural_id"
    - "Async-generator authn dependency so the fail-closed tenancy contextvar set/reset stay in ONE asyncio context (a sync dependency resets across threadpool contexts and raises)"
    - "Login-attempt auditing in the authn dependency: success after verify+tenant-resolve; on AuthError/TenancyError write login-failure then re-raise (success+failure both logged)"
    - "Framework-agnostic lib exceptions mapped at the FastAPI boundary: AuthError->401, ForbiddenError->403, TenancyError->401"
    - "DB-test resolution: VERIDOC_TEST_DATABASE_URL -> testcontainers -> skip (clean-clone harness stays green); live Keycloak round-trip gated on VERIDOC_KEYCLOAK_URL, else real RS256 tokens minted from a local keypair + JWKSCache.from_public_keys (the 01-04 pattern)"

key-files:
  created:
    - services/reference-service/src/reference_service/config.py
    - services/reference-service/src/reference_service/db.py
    - services/reference-service/src/reference_service/models.py
    - services/reference-service/src/reference_service/migrate.py
    - services/reference-service/src/reference_service/main.py
    - services/reference-service/src/reference_service/api/__init__.py
    - services/reference-service/src/reference_service/api/subjects.py
    - services/reference-service/src/reference_service/api/auth_audit.py
    - services/reference-service/migrations/0001_subject.py
    - services/reference-service/Dockerfile
    - services/reference-service/tests/conftest.py
    - services/reference-service/tests/test_subject.py
    - services/reference-service/tests/test_rbac.py
    - services/reference-service/tests/test_login_audit.py
    - services/reference-service/tests/test_field_encryption.py
    - services/reference-service/tests/test_erasure_audit_immutability.py
    - deploy/keycloak/test-users.json
  modified:
    - services/reference-service/src/reference_service/__init__.py
    - services/reference-service/pyproject.toml
    - docs/validation/PACKAGE-LEGITIMACY.md
    - pyproject.toml
    - uv.lock
    - Taskfile.yml
  deleted:
    - services/reference-service/tests/.gitkeep

key-decisions:
  - "The pseudonym token IS the crypto patient_id at rest — one crypto-shred erases both the field ciphertext (undecryptable) and the token (irrecomputable), and the natural_id is never persisted (only its derived token)"
  - "Login-attempt auditing added as missing critical functionality (Rule 2): every login success/failure leaves an immutable audit row (21 CFR Part 11 / Annex 11 access log), wired once in the authn dependency so all phases inherit it"
  - "authn dependency is an async generator (not sync) so the fail-closed tenancy contextvar token survives set->reset within one context; sync dependencies set/reset across different threadpool contexts and raise ValueError"
  - "httpx recorded APPROVED in PACKAGE-LEGITIMACY.md before install (Encode, FastAPI's official TestClient transport) — the 01-04 cryptography precedent; no OIDC-glue package adopted"
  - "pytest --import-mode=importlib so test_rbac.py / test_field_encryption.py can co-exist in a lib AND the reference service without rootdir test-module name collisions"
  - "Live Keycloak round-trip is gated on VERIDOC_KEYCLOAK_URL (Docker-less host has no Keycloak); otherwise real RS256 tokens are minted from a local keypair against the realm contract — the identical verify_token->RBAC->tenancy->audited-encrypted-write code path runs, only the token issuer is local"

requirements-completed: [PLAT-01, PLAT-02, PLAT-03]

# Metrics
duration: ~55min
completed: 2026-06-11
---

# Phase 01 Plan 05: Reference Service Wired End-to-End (D-07 Walking Skeleton) Summary

**The integration point where all five shared platform libs meet: a FastAPI reference service whose `POST/PUT /subjects` path flows HTTP -> Keycloak-style JWT authn + MFA (veridoc-auth) -> deny-by-default RBAC -> fail-closed site/study tenancy (veridoc-tenancy) -> deterministic pseudonym (veridoc-pseudonym) + AES-256-GCM envelope-encrypted PII (veridoc-crypto) -> a SAME-transaction hash-chained audit row (veridoc-audit) -> Postgres, committing the business row and its audit row atomically. Every login attempt (success and failure) is audited, and the GDPR Art. 17 erasure x 21 CFR Part 11 immutability seam is proven once: crypto-shredding patient A leaves the append-only audit chain still verifying (verify_chain True), renders A's audited PII undecryptable, and leaves patient B fully intact. A non-root, secret-free Dockerfile packages it for plan 06.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-06-11
- **Tasks:** 3 (Tasks 1 & 2 TDD RED->GREEN; Task 3 auto)
- **Files:** 17 created, 6 modified, 1 deleted
- **Tests:** 14 reference-service integration tests, all green against live Postgres; full repo suite **80 passed** (libs + service together); clean-clone (no DB/Docker) **59 passed, 21 skipped**.

## Accomplishments

- **D-07 walking skeleton (PLAT-01/02/03):** `reference_service.create_app` builds a FastAPI app that mounts the authn + fail-closed tenancy dependency on the subjects router, exposes an open `/healthz`, and includes `POST /subjects` + `PUT /subjects/{id}`. The create handler derives the pseudonym token, envelope-encrypts the PII, INSERTs the Subject (tenant_id from `current_tenant()`), calls `append_audit` on the SAME session, and commits **once** — business row + hash-chained audit row are atomic (D-05). `verify_chain(session)` is True afterward.
- **Subject model + migration:** `subject` table (id, tenant_id, pseudonym_token, **pii_ciphertext bytea**, created_at, updated_at) via `migrations/0001_subject.py`; `reference_service.migrate` applies the veridoc-audit `audit_log` 0001 then the subject migration (both `apply`/`revert` callable without a full Alembic env, plus Alembic `upgrade`/`downgrade` for CI).
- **RBAC + cross-tenant denial (T-05-03):** a permitted write role (site-coordinator/data-manager/principal-investigator) gets 2xx; a non-permitted realm role (regulatory-affairs) gets **403** (deny-by-default `check_roles`); a caller in another tenant cannot update another tenant's subject (**403**); a token without MFA is rejected **401** at the edge (T-05-05).
- **Login-attempt auditing (Part 11 access log):** every authentication at the edge leaves an immutable audit row — `login-success` (verified subject + tenant) and `login-failure` (best-effort unverified subject + reason) — written in the authn dependency, committed even when the request is rejected.
- **PII encryption at rest (T-05-04):** the raw `pii_ciphertext` column read directly via SQL is **not** the plaintext (and the plaintext bytes do not appear in it); `decrypt_field` round-trips it back under the pseudonym token.
- **The Art. 17 x Part 11 seam (T-05-08, the phase's hardest corner):** create Subjects A and B (each create audit row carries the patient's pseudonym + the base64 envelope ciphertext); `erase_patient(A)` then leaves `verify_chain(session)` **still True** (audit rows immutable/untouched), makes `decrypt_field(A, A's audited ciphertext)` raise `KeyErasedError`, while B's ciphertext still decrypts **and** B's pseudonym still recomputes.
- **Container image (Task 3):** multi-stage `python:3.12-slim` Dockerfile — builder syncs the reference-service member + its five libs via uv (pinned 0.11.20, no dev deps); runtime stage has no toolchain, runs as non-root `USER veridoc`, EXPOSE 8000, `uvicorn reference_service.main:app`. **No secrets baked in** (T-05-02) — config arrives from env/K8s Secrets at runtime (plan 06).
- **Test users (realm contract):** `deploy/keycloak/test-users.json` seeds 6 users across 4 roles and 2 tenants (site-001/study-A, site-002/study-B), all MFA-enabled, matching the plan-04 realm-as-code.

## Task Commits

1. **Task 1 — FastAPI reference service + Subject model through all middleware (RED->GREEN):**
   - RED `b248bce` `test(01-05)` — failing end-to-end Subject create/update + healthz tests + conftest (migrated_engine, in-test JWKS minting real RS256 tokens, keystore isolation, TestClient).
   - GREEN `e3341d0` `feat(01-05)` — config/db/models/migrate/api.subjects/main; httpx recorded APPROVED + service runtime deps; ruff B008 per-file ignore.
2. **Task 2 — Integration tests vs live Postgres (RED->GREEN):**
   - RED `95722a7` `test(01-05)` — test_rbac, test_login_audit, test_field_encryption, test_erasure_audit_immutability + test-users.json.
   - GREEN `7b1a5cc` `feat(01-05)` — `auth_audit.py` (login success/failure auditing wired into the authn dependency) + create audit `after` carries base64 ciphertext.
3. **Task 3 — Dockerfile:** `4f4cbec` `feat(01-05)` — non-root, secret-free, uvicorn multi-stage image.
4. **Test infra:** `e5bae2f` `chore(01-05)` — pytest `--import-mode=importlib` (duplicate test basenames across lib+service) + reference-service integration in `task test:integration`.

**Plan metadata:** committed separately with this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md updates.

## Verification

- `uv run pytest services/reference-service/tests/ -x -q` (env `VERIDOC_TEST_DATABASE_URL`) -> **14 passed**.
- Task 1 (`-k "subject or health"`) and Task 2 (rbac/login-audit/field-encryption/erasure) acceptance commands both green.
- Full repo suite (`uv run pytest`, shared Postgres) -> **80 passed**; clean-clone (no DB/Docker) -> **59 passed, 21 skipped** (Wave 0 harness stays green).
- `uv run ruff check .` + `uv run ruff format --check .` -> clean across the whole repo.
- Dockerfile: `test -f` + `grep uvicorn` + `grep USER` pass; secret scan finds no hard-coded credentials.
- Packages installed: `fastapi 0.136.3`, `uvicorn 0.49.0`, `pydantic-settings 2.14.1`, `httpx 0.28.1`, `starlette 1.2.1` — all APPROVED (httpx recorded before install). No OIDC-glue package adopted.

## Decisions Made

- **Pseudonym token = crypto patient_id at rest** so a single `erase_patient(token)` crypto-shreds both the ciphertext and the token; the natural_id is never persisted.
- **Login auditing wired in the authn dependency** (success + failure), so the Part 11 access-log behaviour is established once and inherited by Phases 2-7.
- **Async-generator authn dependency** to keep the fail-closed tenancy contextvar token in one context (sync dependencies set/reset across threadpool contexts and raise).
- **httpx recorded APPROVED before install** (Encode, FastAPI's official test transport) — the supply-chain gate honoured exactly as plan 04 did for `cryptography`.
- **pytest importlib import mode** to allow shared test-module basenames across a lib and the service.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical functionality] httpx recorded in PACKAGE-LEGITIMACY.md before install (supply-chain gate)**
- **Found during:** Task 1 (test transport).
- **Issue:** `fastapi.testclient.TestClient` requires `httpx`, which was not yet in the APPROVED supply-chain table; silently installing an unlisted package is forbidden.
- **Fix:** Added an `httpx` row (verdict APPROVED — Encode, `github.com/encode/httpx`, FastAPI's official test dependency, same org as Starlette/uvicorn) plus a plan-05 resolution note to `docs/validation/PACKAGE-LEGITIMACY.md`, **then** installed. The other newly-installed packages (fastapi, uvicorn, pydantic-settings) were already APPROVED.
- **Files modified:** `docs/validation/PACKAGE-LEGITIMACY.md`, `services/reference-service/pyproject.toml`, root `pyproject.toml`, `uv.lock`.
- **Commit:** `e3341d0`.

**2. [Rule 2 - Critical functionality] Login-attempt auditing was implied by the plan's tests but not in the Task-1 wiring**
- **Found during:** Task 2 (test_login_audit).
- **Issue:** The plan requires every login attempt (success AND failure) to produce an audit row (a 21 CFR Part 11 / Annex 11 access-control requirement), but the Task-1 handler only audited Subject writes.
- **Fix:** Added `api/auth_audit.py` and wired `audit_login_success` / `audit_login_failure` into the authn dependency — success after verify+tenant-resolve, failure on `AuthError`/`TenancyError` before re-raising. Each login event commits its own append-only row; the chain still verifies.
- **Files modified:** `services/reference-service/src/reference_service/api/auth_audit.py` (new), `services/reference-service/src/reference_service/main.py`.
- **Commit:** `7b1a5cc`.

**3. [Rule 3 - Blocking] Async authn dependency (tenancy contextvar reset across threadpool contexts)**
- **Found during:** Task 1 GREEN.
- **Issue:** A synchronous generator authn dependency set the tenancy contextvar in one threadpool context and tried to reset it in another at teardown -> `ValueError: Token was created in a different Context`.
- **Fix:** Made the authn dependency an `async def` generator so setup + teardown share one asyncio context; the sync route handlers run in a threadpool that inherits a copy of that context (so `current_tenant()` reads the bound tenant), and the reset happens back in the async context.
- **Files modified:** `services/reference-service/src/reference_service/main.py`.
- **Commit:** `e3341d0`.

**4. [Rule 3 - Blocking] Docker absent -> DB-backed tests via the local least-privilege Postgres; live Keycloak gated**
- **Found during:** Tasks 1 & 2.
- **Issue:** Docker is not available on this host (RESEARCH Pitfall 6), so neither a testcontainers Postgres nor a live Keycloak container can start; the plan calls for "live Keycloak + Postgres".
- **Fix:** (a) DB — followed the 01-02/01-03/01-04 resolve order: provisioned a reference-service test DB (`veridoc_reference_test`) owned by the existing least-privilege `veridoc_test` role and ran the integration tests against it via `VERIDOC_TEST_DATABASE_URL` (TCP + scram password); tests skip cleanly with no env/Docker. (b) Keycloak — gated a live round-trip on `VERIDOC_KEYCLOAK_URL`; absent that, the tests mint **real RS256 access tokens** from a local keypair served through `JWKSCache.from_public_keys`, exercising the identical `verify_token` -> RBAC -> tenancy -> audited-encrypted-write code path against the realm-as-code contract (issuer/audience/claims/MFA/roles/site-study read from `deploy/keycloak/veridoc-realm.json` + `test-users.json`). Only the token *issuer* is local; the live-Keycloak token round-trip lands in plan 06 CI where containers run.
- **Files:** `services/reference-service/tests/conftest.py` (design).
- **Commit:** `b248bce` / `e3341d0`.

**5. [Rule 3 - Blocking] Duplicate test-module basenames across lib and service broke aggregate collection**
- **Found during:** full-repo verification.
- **Issue:** `test_rbac.py` (veridoc-auth) and `test_field_encryption.py` (veridoc-crypto) share basenames with the new reference-service tests; under pytest's default prepend import mode the aggregate run (`uv run pytest` / `task test:unit`) failed collection with a duplicate-module error.
- **Fix:** Set `--import-mode=importlib` in the root pytest config (no `__init__.py` churn in existing lib tests). Whole-repo suite now collects and passes (80 passed with DB; 59 passed / 21 skipped clean-clone).
- **Files modified:** root `pyproject.toml`.
- **Commit:** `e5bae2f`.

**Total deviations:** 5 (2 critical functionality, 3 blocking). No architectural changes; no scope creep; all installs within the APPROVED legitimacy table (httpx recorded APPROVED before install). No OIDC-glue package adopted.

## Issues Encountered

- A Starlette deprecation warning (`Using httpx with starlette.testclient is deprecated; install httpx2`) is emitted by the current Starlette/httpx pairing — non-blocking, out of scope (no `httpx2` install; httpx remains the APPROVED, working transport). Logged here for plan-06 awareness.

## Known Stubs

None that block the plan goal. The Subject is a deliberately-thin reference entity (RESEARCH Open Question #3) — it exercises every cross-cutting concern without later-phase domain logic, exactly as intended. The KMS cloud adapters (`AwsKmsKeyring`/`AzureKeyVaultKeyring`) remain interface stubs from plan 03 (DEC-cloud-provider OPEN); the reference service uses the working `LocalKeyring` master key via `VERIDOC_MASTER_KEY`. The Alembic `env.py` runner is still deferred to plan 06 CI (the migrations are directly callable and fully exercised here via `reference_service.migrate`).

## Threat Flags

None. All security-relevant surface introduced (the `/subjects` write path, the `/healthz` open route, the subject schema) is covered by the plan's `<threat_model>` (T-05-01..08) and asserted by tests. The only unauthenticated route is `/healthz` (T-05-07 accepted: rate-limiting deferred).

## TDD Gate Compliance

Tasks 1 & 2 followed RED->GREEN: each `test(01-05)` commit precedes its `feat(01-05)` commit in git history (`b248bce`->`e3341d0`, `95722a7`->`7b1a5cc`). No REFACTOR commits were needed (implementations were clean on first green; ruff lint/format applied within the GREEN steps). Task 3 (Dockerfile) is a non-TDD artifact task.

## Next Plan Readiness

- The reference service is the cloneable D-07 template: Phases 2-7 reuse this exact authn->RBAC->tenancy->pseudonym+encrypt->same-txn-audit->Postgres path for their own entities.
- Plan 01-06 (CI + kind) builds + loads `services/reference-service/Dockerfile`, imports `deploy/keycloak/veridoc-realm.json` + `deploy/keycloak/test-users.json` into a live Keycloak, sets `VERIDOC_KEYCLOAK_URL` + `VERIDOC_TEST_DATABASE_URL` (or a Docker Postgres) so the DB- and Keycloak-backed tests run in the pipeline, adds an Alembic `env.py` to run both migrations, and injects `REFERENCE_SERVICE_CLIENT_SECRET` + the KMS master key from K8s Secrets.

## Self-Check: PASSED

All 17 declared created key-files verified present on disk; all six task/infra commits (`b248bce`, `e3341d0`, `95722a7`, `7b1a5cc`, `4f4cbec`, `e5bae2f`) verified in git history. `uv run pytest services/reference-service/tests/` exits 0 (14 passed against the local least-privilege Postgres); full repo 80 passed; clean-clone 59 passed / 21 skipped; `uv run ruff check .` + `ruff format --check .` clean repo-wide. Dockerfile present, non-root, secret-free. All installed packages APPROVED (httpx recorded before install); no OIDC-glue package installed.

---
*Phase: 01-platform-skeleton-audit-foundation*
*Completed: 2026-06-11*
