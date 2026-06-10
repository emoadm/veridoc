---
phase: 01-platform-skeleton-audit-foundation
plan: 04
subsystem: auth-tenancy
tags: [keycloak, oidc, jwks, pyjwt, jwcrypto, rs256, mfa, acr, rbac, 8-roles, tenancy, contextvar, fail-closed, ip-allowlist, realm-as-code, d-01, d-02, d-03, plat-03]

# Dependency graph
requires:
  - 01-01 uv workspace members libs/veridoc-auth + libs/veridoc-tenancy + APPROVED package gate (pyjwt, jwcrypto)
provides:
  - "veridoc_auth.verify_token(token, *, jwks, issuer, audience) -> Principal (RS256-pinned JWKS verify + iss/aud/exp + MFA acr/amr)"
  - "veridoc_auth.authn_dependency(*, jwks, issuer, audience) -> dependency(authorization) -> Principal (Bearer wrapper)"
  - "veridoc_auth.require_role(*roles) / check_roles(principal, allowed) -> deny-by-default 8-role RBAC (403)"
  - "veridoc_auth.ip_allowlist_check(client_ip, *, tenant, allowlists) -> data-driven per-tenant IP-allowlist hook"
  - "veridoc_auth.JWKSCache (kid-keyed, TTL refresh, jwcrypto JWK parse, offline from_public_keys/from_jwks_document ctors)"
  - "veridoc_auth.Principal(subject, roles, tenant_claims, acr, amr) + AuthError(401)/ForbiddenError(403) + EIGHT_ROLES"
  - "veridoc_tenancy.current_tenant() -> Tenant (raises TenancyError if unset — fail-closed, never default)"
  - "veridoc_tenancy.tenant_scope / set_tenant / reset_tenant / tenant_from_claims (fail-closed claim extraction)"
  - "veridoc_tenancy.tenancy_middleware(principal) + build_asgi_tenancy_middleware(getter) + Tenant/TenancyError"
  - "deploy/keycloak/veridoc-realm.json (realm-as-code: 8 roles, browser-mfa REQUIRED OTP flow, reference-service OIDC client + audience mapper, acr.loa.map, session timeouts)"
  - "docs/validation/RBAC-MATRIX.md (8-role -> resource/action permission matrix; deny-by-default; Annex 11 / Part 11 evidence)"
affects: [01-05-reference-service]

# Tech tracking
tech-stack:
  added: [pyjwt 2.13.0, jwcrypto 1.5.7, cryptography 48.0.1]
  patterns:
    - "OIDC JWT verify: resolve kid -> JWKS public key, decode with algorithms=['RS256'] pinned (rejects alg=none + HS256 confusion), verify iss/aud/exp, assert MFA via acr=mfa OR amr contains otp (API-tier MFA enforcement, not just Keycloak policy)"
    - "Deny-by-default RBAC: require_role(*roles) passes only if the principal holds >=1 of the explicitly required realm roles, else 403; no implicit inheritance"
    - "Data-driven IP-allowlist hook: per-tenant CIDR map; allow when unset (opt-in), deny unlisted IP (not a hard-coded list)"
    - "Fail-closed tenancy: Tenant(site, study) in a contextvar; current_tenant() raises TenancyError when unset (never a default); contextvars give per-asyncio-task isolation (no cross-request leak)"
    - "Realm-as-code: 8 roles + browser-mfa REQUIRED OTP flow + acr.loa.map + confidential OIDC client w/ audience+role+tenant mappers committed as an importable JSON (Pitfall 4); client secret is a placeholder, no plaintext secrets in git"

key-files:
  created:
    - deploy/keycloak/veridoc-realm.json
    - docs/validation/RBAC-MATRIX.md
    - libs/veridoc-auth/src/veridoc_auth/errors.py
    - libs/veridoc-auth/src/veridoc_auth/jwks.py
    - libs/veridoc-auth/src/veridoc_auth/middleware.py
    - libs/veridoc-auth/src/veridoc_auth/rbac.py
    - libs/veridoc-auth/src/veridoc_auth/allowlist.py
    - libs/veridoc-auth/tests/test_realm_config.py
    - libs/veridoc-auth/tests/test_jwt_verify.py
    - libs/veridoc-auth/tests/test_rbac.py
    - libs/veridoc-tenancy/src/veridoc_tenancy/context.py
    - libs/veridoc-tenancy/src/veridoc_tenancy/middleware.py
    - libs/veridoc-tenancy/tests/test_tenancy_failclosed.py
  modified:
    - libs/veridoc-auth/src/veridoc_auth/__init__.py
    - libs/veridoc-auth/pyproject.toml
    - libs/veridoc-tenancy/src/veridoc_tenancy/__init__.py
    - docs/validation/PACKAGE-LEGITIMACY.md
    - uv.lock

key-decisions:
  - "No OIDC-glue package adopted: Keycloak JWTs are verified directly with the already-APPROVED pyjwt[crypto] + jwcrypto (decision-context preference). fastapi-keycloak-middleware / authlib remain NOT installed."
  - "cryptography (PyCA) added to PACKAGE-LEGITIMACY.md with a verified verdict before install — the authentic, required transitive dependency of pyjwt[crypto]/jwcrypto for RS256 (no silent unlisted install)."
  - "RS256 is pinned (algorithms=['RS256']) AND the header alg is pre-checked, so alg=none and HS256 algorithm-confusion are both rejected (T-04-01)."
  - "MFA is enforced in the API tier: acr in {mfa} OR amr intersects {otp,mfa,hwk,sms}; a token without MFA is rejected (T-04-02), defence-in-depth over the realm's REQUIRED OTP flow."
  - "Tenancy is fail-closed via a contextvar with no default: current_tenant() raises TenancyError when unset, and tenant_from_claims raises when site/study are absent (T-04-04, D-03)."
  - "Client secret in the realm export is a \${REFERENCE_SERVICE_CLIENT_SECRET} placeholder resolved from a K8s Secret at deploy (plan 01-06) — no plaintext secrets in git (T-04-06)."

requirements-completed: [PLAT-03]

# Metrics
duration: ~25min
completed: 2026-06-11
---

# Phase 01 Plan 04: veridoc-auth + veridoc-tenancy (OIDC/MFA/RBAC + Fail-Closed Tenancy) Summary

**The identity-and-access core of the platform: `veridoc-auth` verifies Keycloak-issued JWTs against the realm JWKS (RS256-pinned signature + iss/aud/exp), enforces MFA via the acr/amr claim in the API tier, and provides deny-by-default 8-role RBAC plus a data-driven per-tenant IP-allowlist hook; `veridoc-tenancy` carries the request-scoped (site, study) tenant in a fail-closed contextvar so no query can ever run unscoped; and the 8 roles + MFA OTP flow + OIDC client are committed as an importable Keycloak realm-as-code (Pitfall 4 closed). PLAT-03 is now complete.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-06-11
- **Tasks:** 3 (all TDD RED -> GREEN)
- **Files:** 13 created, 5 modified
- **Tests:** 32 new (6 realm-config + 19 JWT-verify/RBAC + 7 tenancy), all green with no cloud / no DB / no Docker.

## Accomplishments

- **Keycloak realm-as-code (D-01, D-02, Pitfall 4):** `deploy/keycloak/veridoc-realm.json` is an `--import-realm`-loadable export declaring realm `veridoc`, the 8 D-02 realm roles (cra, data-manager, medical-monitor, site-coordinator, principal-investigator, sponsor-rep, regulatory-affairs, system-admin) with distinct access-level attributes, a confidential OIDC `reference-service` client with an `oidc-audience-mapper` (so `aud=reference-service`) plus realm-role and site/study tenant-claim mappers, a `browser-mfa` flow with a **REQUIRED** OTP step, an `acr.loa.map` defining `mfa`, and SSO idle/max session timeouts. No plaintext secrets (client secret is a placeholder).
- **RBAC matrix (validation evidence):** `docs/validation/RBAC-MATRIX.md` maps each of the 8 roles to a resource×action permission matrix (deny-by-default, distinct access levels, tenancy-scoping note, traceability table) — Annex 11 / Part 11 access-control evidence under change control.
- **OIDC authn middleware (D-01/D-02, Pattern 2, T-04-01/02):** `verify_token` resolves the signing key by `kid` from a `JWKSCache`, decodes with `algorithms=["RS256"]` pinned (and a pre-check that rejects `alg=none`/HS256), verifies `iss`/`aud`/`exp`, asserts the MFA claim (`acr=mfa` or `amr` contains `otp`), and returns a `Principal(subject, roles, tenant_claims, acr, amr)`. `authn_dependency` wraps a Bearer header.
- **Deny-by-default 8-role RBAC (T-04-03):** `require_role(*roles)` / `check_roles` pass only when the principal holds one of the explicitly required realm roles, else `ForbiddenError` (403). `require_role` validates role names against the canonical `EIGHT_ROLES`.
- **Data-driven IP-allowlist hook (T-04-07):** `ip_allowlist_check(client_ip, *, tenant, allowlists)` consults a per-tenant CIDR map — allows when no allowlist is configured for the tenant, denies a non-listed IP when one is. Not a hard-coded list.
- **Fail-closed tenancy (D-03, Pattern 3, T-04-04):** `current_tenant()` returns the request `Tenant(site, study)` from a contextvar and **raises `TenancyError` when unset** (never a default). `tenant_from_claims` raises when site/study are missing. `tenancy_middleware(principal)` sources the tenant from the auth `Principal.tenant_claims` and binds it for the request, clearing after; contextvar isolation proven no-leak under concurrent asyncio tasks.

## Task Commits

1. **Task 1 — Keycloak realm-as-code + RBAC matrix (RED -> GREEN):**
   - RED `8017d1b` `test(01-04)` — failing realm-config structural tests (8 roles, OIDC client + audience mapper, REQUIRED OTP flow, acr.loa.map, session timeouts).
   - GREEN `3ad0d90` `feat(01-04)` — `veridoc-realm.json` + `RBAC-MATRIX.md`.
2. **Task 2 — OIDC authn middleware (JWKS verify + MFA) + 8-role RBAC (RED -> GREEN):**
   - RED `9f441e9` `test(01-04)` — failing JWT-verify (accept/reject matrix) + RBAC + allowlist tests.
   - GREEN `4be7d12` `feat(01-04)` — `jwks.py`, `middleware.py`, `rbac.py`, `allowlist.py`, `errors.py`, exports; `pyjwt[crypto]`+`jwcrypto` installed; `cryptography` recorded APPROVED in PACKAGE-LEGITIMACY.md.
3. **Task 3 — fail-closed request-scoped tenancy context (RED -> GREEN):**
   - RED `53666fa` `test(01-04)` — failing fail-closed + isolation tests.
   - GREEN `aec2144` `feat(01-04)` — `context.py` (contextvar + Tenant/TenancyError + tenant_scope + tenant_from_claims), `middleware.py` (tenancy_middleware + ASGI factory), exports.
4. **Test formatting:** `8149331` `style(01-04)` — ruff import-sort/line-wrap on the test modules (no behavioral change; applied after the RED commits).

**Plan metadata:** committed separately with this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md updates.

## Verification

- `uv run pytest libs/veridoc-auth/tests/ libs/veridoc-tenancy/tests/ -q` -> **32 passed** (plan verification).
- Realm JSON valid + all 8 roles present (`uv run python -c "...need.issubset(roles)"` exits 0); 6 realm-config tests assert the OIDC client/audience mapper, the REQUIRED OTP flow, acr.loa.map, and session timeouts.
- Auth: valid+MFA token accepted; bad-sig / alg=none / HS256 / wrong-iss / wrong-aud / expired / unknown-kid / missing-MFA all rejected (`test_jwt_verify.py`). Cross-role request -> 403; deny-by-default with no roles (`test_rbac.py`).
- Tenancy: unset context raises; set context returns the Tenant; tenant_scope clears on exit; no cross-request leak under concurrent asyncio tasks (`test_tenancy_failclosed.py`).
- Full lib suite (`uv run pytest libs/ -q`) -> **59 passed, 7 skipped** (the audit DB-backed tests skip cleanly with no Docker — plan 01-02/01-03 resolve->testcontainers->skip pattern); crypto/pseudonym/auth/tenancy unaffected.
- `uv run ruff check .` -> clean across the whole repo.
- Packages: `pyjwt 2.13.0`, `jwcrypto 1.5.7`, `cryptography 48.0.1` installed — all APPROVED (cryptography recorded with a verified verdict before install). `fastapi-keycloak-middleware`/`authlib` NOT installed.

## Decisions Made

- **No OIDC-glue package** — verified Keycloak JWTs directly with the already-APPROVED `pyjwt[crypto]` + `jwcrypto`, per the decision-context preference; avoided adopting an unlisted middleware package.
- **`cryptography` (PyCA) recorded APPROVED before install** — it is the authentic, required transitive dependency of `pyjwt[crypto]`/`jwcrypto` for RS256. Added a row + a plan-04 resolution note to PACKAGE-LEGITIMACY.md rather than silently installing an unlisted package.
- **RS256 pinned + header pre-check** so `alg=none` and HS256 confusion are both rejected.
- **MFA enforced in the API tier** (`acr=mfa` or `amr` otp) as defence-in-depth over the realm's REQUIRED OTP flow.
- **Tenancy fail-closed via a contextvar with no default** — `current_tenant()` and `tenant_from_claims` both raise rather than ever returning an unscoped/partial tenant.
- **veridoc-tenancy duck-types `Principal.tenant_claims`** (Protocol) so it carries no hard runtime dependency on veridoc-auth; the Starlette middleware factory imports Starlette lazily.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical functionality] `cryptography` recorded in PACKAGE-LEGITIMACY.md before install (supply-chain gate)**
- **Found during:** Task 2 (auth deps).
- **Issue:** RS256 JWKS verification requires the `cryptography` package (via `pyjwt[crypto]`/`jwcrypto`), which was not yet in the APPROVED supply-chain table. The decision context forbids silently installing unlisted packages.
- **Fix:** Added a `cryptography` row (verdict APPROVED — authentic PyCA, `github.com/pyca/cryptography`, the required transitive dep of two already-APPROVED packages) plus a plan-04 OIDC-glue resolution note to `docs/validation/PACKAGE-LEGITIMACY.md`, **then** installed. No OIDC-glue package was adopted.
- **Files modified:** `docs/validation/PACKAGE-LEGITIMACY.md`, `libs/veridoc-auth/pyproject.toml`, `uv.lock`.
- **Commit:** `4be7d12`.

**2. [Rule 3 - Blocking] Docker absent — auth/tenancy tests run with no container**
- **Found during:** Tasks 2 & 3.
- **Issue:** Docker is not available on this host (RESEARCH Pitfall 6); the sequential-execution note directs following the 01-02/01-03 resolve->testcontainers->skip pattern for any DB/Keycloak-dependent tests.
- **Fix:** Neither lib needs a container: JWT-verify tests use a locally generated RSA keypair + an in-test `JWKSCache.from_public_keys` (no live Keycloak — that round-trip is plan 01-05), and tenancy tests use contextvars only. All 32 tests run on a clean clone with no cloud/DB/Docker, matching the Wave 0 harness contract.
- **Files:** n/a (design choice — offline JWKS ctor + in-memory contextvar).
- **Commit:** n/a (inherent to the implementation).

**Total deviations:** 2 (1 critical supply-chain gate, 1 blocking-environment). No architectural changes; no scope creep; the only newly-installed packages are `pyjwt[crypto]` + `jwcrypto` (APPROVED) and their authentic PyCA transitive `cryptography` (recorded APPROVED before install).

## Known Stubs

- `build_asgi_tenancy_middleware` imports Starlette **lazily** and is exercised end-to-end by the reference service (plan 01-05), which provides the `principal_getter` from its auth dependency and a live ASGI app. The core fail-closed logic it delegates to (`tenancy_middleware` / `tenant_scope` / `tenant_from_claims`) is fully tested here. This is a wiring seam for 01-05, not unwired behavior.
- `JWKSCache._refresh` (live HTTP JWKS fetch) is `# pragma: no cover` this plan — the live Keycloak token round-trip is plan 01-05; the offline constructors (`from_public_keys` / `from_jwks_document`) and the kid-resolution/rotation logic are fully tested.

These do not block the plan goal (signature+MFA verify, RBAC, fail-closed tenancy all work end-to-end against an in-test JWKS); the live Keycloak round-trip lands in 01-05 per the plan's own objective.

## TDD Gate Compliance

All three tasks followed RED -> GREEN: each `test(01-04)` commit precedes its `feat(01-04)` commit in git history (`8017d1b`->`3ad0d90`, `9f441e9`->`4be7d12`, `53666fa`->`aec2144`). No REFACTOR commits were needed (implementations were clean on first green; lint/format applied within/after GREEN). The trailing `style(01-04)` commit is formatting-only on the test modules.

## Next Plan Readiness

- `veridoc_auth` exports `verify_token`, `authn_dependency`, `require_role`, `check_roles`, `ip_allowlist_check`, `Principal`, `JWKSCache`, `AuthError`, `ForbiddenError`, `EIGHT_ROLES`; `veridoc_tenancy` exports `current_tenant`, `tenant_scope`, `set_tenant`, `reset_tenant`, `tenant_from_claims`, `tenancy_middleware`, `build_asgi_tenancy_middleware`, `Tenant`, `TenancyError`. Plan 01-05 (reference service) mounts these on a FastAPI app: authn dependency -> RBAC `require_role` -> tenancy middleware (from `Principal.tenant_claims`) -> business handler -> envelope-encrypted PII (01-03) -> same-transaction hash-chained audit (01-02).
- Plan 01-05 exercises the **live** Keycloak token round-trip in a real realm (seeded users with MFA enrolled), wires `JWKSCache` to the realm JWKS endpoint, and supplies the `principal_getter` for `build_asgi_tenancy_middleware`.
- Plan 01-06 (Helm/CI) loads `deploy/keycloak/veridoc-realm.json` via `--import-realm` and injects `REFERENCE_SERVICE_CLIENT_SECRET` from a K8s Secret.

## Self-Check: PASSED

All 14 declared key-files (13 created + this SUMMARY) verified present on disk; all six task commits (`8017d1b`, `3ad0d90`, `9f441e9`, `4be7d12`, `53666fa`, `aec2144`) + the `8149331` style commit verified in git history. `uv run pytest libs/veridoc-auth/tests/ libs/veridoc-tenancy/tests/ -q` exits 0 (32 passed) with no cloud / no DB / no Docker; full lib suite 59 passed / 7 skipped; `uv run ruff check .` clean repo-wide. Realm JSON valid + all 8 roles present. `pyjwt`/`jwcrypto`/`cryptography` installed (all APPROVED); no OIDC-glue package installed.

---
*Phase: 01-platform-skeleton-audit-foundation*
*Completed: 2026-06-11*
