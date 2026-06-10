# Phase 01 Validation Plan — Platform Skeleton & Audit Foundation

> **GAMP 5 validation-READY evidence backbone** (DEC-gamp5-csv). This document maps every
> Phase-1 Success Criterion to the automated test that proves it. It is *validation-ready*
> documentation only — no IQ/OQ/PQ execution happens this phase; PQ + production access gate
> *commercial* deployment, not this build (CON-gamp5-csv).
>
> Source: `01-VALIDATION.md` § Per-Task Verification Map + `01-RESEARCH.md` § Validation
> Architecture. Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky.

## Test Infrastructure (Wave 0)

| Property | Value |
|----------|-------|
| Python framework | **pytest** (`uv run pytest`) — config in root `pyproject.toml [tool.pytest.ini_options]` (testpaths = libs, services; addopts = `-x -q`) |
| JS/TS framework | **Vitest** (`pnpm -r vitest run`) — config in root `vitest.config.ts` (jsdom + @testing-library/react) |
| Quick run command | `task test:unit` — runs pytest + vitest; fast, no cluster/containers |
| Full suite command | `task test` — Wave 0 = test:unit; later plans extend with integration (Postgres/Redis/Keycloak/kind) |
| Lint | `task lint` — ruff check + ruff format --check + pnpm -r lint |
| Build | `task build` — uv build + pnpm -r build |

## Success Criterion → Test Map

| Success Criterion | Requirement | Secure Behavior | Test Type | Automated Command | Lands in plan | Status |
|-------------------|-------------|-----------------|-----------|-------------------|---------------|--------|
| **SC#1** | PLAT-01 | Scaffold builds + lints + deploys to a real (kind) cluster green | integration (CI) | `task lint && task build` locally; `kind create cluster && helm install … && kubectl wait …` in GitHub Actions | 01-01 (build/lint), 01-06 (kind deploy) | ⬜ pending |
| **SC#2** | PLAT-02 | Every action → append-only hash-chained record (identity/role/ts/before-after) | unit + integration | `uv run pytest libs/veridoc-audit/tests/test_chain.py -x` | 01-02 | ⬜ pending |
| **SC#2** | PLAT-02 | **Tamper is detectable** — mutate a prior row, re-walk chain, expect failure (THE gate) | integration | `uv run pytest libs/veridoc-audit/tests/test_tamper_detection.py::test_mutated_row_breaks_chain -x` | 01-02 | ⬜ pending |
| **SC#2** | PLAT-02 | Audit + business write atomic (force audit fail → business rolls back) | integration | `uv run pytest libs/veridoc-audit/tests/test_same_txn.py -x` | 01-02 / 01-05 | ⬜ pending |
| **SC#2** | PLAT-02 | Canonical serialization stable (golden vector) | unit | `uv run pytest libs/veridoc-audit/tests/test_jcs_golden.py -x` | 01-02 | ⬜ pending |
| **SC#3** | PLAT-03 | Auth with one of 8 roles behind MFA; role sees only permitted access | integration | `uv run pytest services/reference-service/tests/test_rbac.py` (assert 403 cross-role; MFA acr enforced) | 01-04 / 01-05 | ⬜ pending |
| **SC#3** | PLAT-03 | All login attempts (success + failure) audited | integration | `uv run pytest services/reference-service/tests/test_login_audit.py` | 01-04 / 01-05 | ⬜ pending |
| **SC#4** | PLAT-03 | PII field-level encrypted at rest (ciphertext in DB, not plaintext) | integration | `uv run pytest services/reference-service/tests/test_field_encryption.py` | 01-03 / 01-05 | ⬜ pending |
| **SC#4** | PLAT-03 | Deterministic pseudonym: same patient → same token across calls | unit | `uv run pytest libs/veridoc-pseudonym/tests/test_pseudonym_deterministic.py` | 01-03 | ⬜ pending |
| **SC#4** | PLAT-03 | Erasure: delete patient key → token irrecomputable + ciphertext undecryptable | integration | `uv run pytest libs/veridoc-crypto/tests/test_crypto_shred.py` | 01-03 | ⬜ pending |

## Wave 0 Status (this plan, 01-01)

- [x] `pyproject.toml [tool.pytest.ini_options]` + `Taskfile.yml` test targets (`install`, `lint`, `test:unit`, `test`, `build`)
- [x] root `vitest.config.ts` (jsdom + @testing-library/react)
- [x] One passing pytest smoke test (`libs/veridoc-audit/tests/test_smoke.py`) — `uv run pytest` collects ≥1 test
- [x] One passing Vitest smoke test (`apps/web/src/App.test.tsx`) — renders App, asserts heading
- [ ] Real audit/crypto/pseudonym/service tests — land in plans 01-02 … 01-05 (rows above)
- [ ] CI workflow `.github/workflows/ci.yml` with kind-action deploy stage — plan 01-06
- [ ] Integration fixtures (testcontainers Postgres/Redis, Keycloak realm-import) — plans 01-02 … 01-05

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MFA enrollment UX flow | PLAT-03 | Full TOTP enrollment is an interactive browser flow | Log in as a seeded role, enroll TOTP, confirm `acr=mfa` in the issued token. Automated coverage exists for the security-relevant assertion (`acr` enforced); the enrollment UX itself is manual. |

## GAMP 5 posture

- **Validation-READY, not validation-EXECUTED.** This phase produces the evidence backbone
  (URS→FS→test map) but does not run IQ/OQ/PQ; those gate commercial deployment (DEC-gamp5-csv,
  CON-iq-oq-pq-validation).
- The package-legitimacy review (`docs/validation/PACKAGE-LEGITIMACY.md`) is the supply-chain
  control of record for this phase (threat T-01-SC).
