---
phase: 1
slug: platform-skeleton-audit-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 01-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python services/libs) + Vitest (React/TS scaffold) — none configured yet; Wave 0 installs |
| **Config file** | none yet — Wave 0 creates `pyproject.toml [tool.pytest]` + `vitest.config.ts` |
| **Quick run command** | `task test:unit` (uv run pytest -x -q; pnpm vitest run) |
| **Full suite command** | `task test` (unit + integration incl. kind deploy + tamper-detection) |
| **Estimated runtime** | ~30s unit; integration adds Keycloak/Postgres/kind (minutes, CI) |

---

## Sampling Rate

- **After every task commit:** Run `task test:unit` (chain, JCS golden, pseudonym determinism — fast, no cluster)
- **After every plan wave:** Run `task test` (adds Keycloak/Postgres integration via docker-compose or kind)
- **Before `/gsd:verify-work`:** Full suite green in GitHub Actions including the kind deploy + tamper-detection test
- **Max feedback latency:** ~30 seconds for unit sampling

---

## Per-Task Verification Map

| Success Criterion | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|-------------------|-------------|-----------------|-----------|-------------------|-------------|--------|
| SC#1 | PLAT-01 | Scaffold builds + lints + deploys to a real (kind) cluster green | integration (CI) | `kind create cluster && helm install … && kubectl wait …` in GitHub Actions | ❌ W0 | ⬜ pending |
| SC#2 | PLAT-02 | Every action → append-only hash-chained record (identity/role/ts/before-after) | unit + integration | `pytest libs/veridoc-audit/tests/test_chain.py -x` | ❌ W0 | ⬜ pending |
| SC#2 | PLAT-02 | **Tamper is detectable** — mutate a prior row, re-walk chain, expect failure | integration (THE gate) | `pytest …/test_tamper_detection.py::test_mutated_row_breaks_chain -x` | ❌ W0 | ⬜ pending |
| SC#2 | PLAT-02 | Audit + business write atomic (force audit fail → business rolls back) | integration | `pytest …/test_same_txn.py -x` | ❌ W0 | ⬜ pending |
| SC#2 | PLAT-02 | Canonical serialization stable (golden vector) | unit | `pytest …/test_jcs_golden.py -x` | ❌ W0 | ⬜ pending |
| SC#3 | PLAT-03 | Auth with one of 8 roles behind MFA; role sees only permitted access | integration | `pytest …/test_rbac.py` (assert 403 cross-role; MFA acr enforced) | ❌ W0 | ⬜ pending |
| SC#3 | PLAT-03 | All login attempts (success + failure) audited | integration | `pytest …/test_login_audit.py` | ❌ W0 | ⬜ pending |
| SC#4 | PLAT-03 | PII field-level encrypted at rest (ciphertext in DB, not plaintext) | integration | `pytest …/test_field_encryption.py` | ❌ W0 | ⬜ pending |
| SC#4 | PLAT-03 | Deterministic pseudonym: same patient → same token across calls | unit | `pytest …/test_pseudonym_deterministic.py` | ❌ W0 | ⬜ pending |
| SC#4 | PLAT-03 | Erasure: delete patient key → token irrecomputable + ciphertext undecryptable | integration | `pytest …/test_crypto_shred.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml [tool.pytest]` + `Taskfile.yml` test targets — no test framework configured yet
- [ ] `vitest.config.ts` for the web scaffold
- [ ] `libs/veridoc-audit/tests/` — chain, tamper-detection, same-txn, JCS golden vector
- [ ] `libs/veridoc-crypto/tests/` + `libs/veridoc-pseudonym/tests/` — encryption round-trip, determinism, crypto-shred
- [ ] `services/reference-service/tests/` — RBAC (Keycloak fixture), login-attempt audit, field-encryption at rest
- [ ] CI workflow `.github/workflows/ci.yml` with kind-action deploy stage
- [ ] Test fixtures: synthetic patient data, ephemeral Postgres/Redis (testcontainers or compose), Keycloak realm-import

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MFA enrollment UX flow | PLAT-03 | Full TOTP enrollment is an interactive browser flow | Log in as a seeded role, enroll TOTP, confirm acr=mfa in token |

*Automated coverage exists for the security-relevant assertion (acr enforced); the enrollment UX itself is manual.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (unit sampling)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
