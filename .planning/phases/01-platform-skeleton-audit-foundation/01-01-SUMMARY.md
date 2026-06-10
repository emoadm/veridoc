---
phase: 01-platform-skeleton-audit-foundation
plan: 01
subsystem: infra
tags: [uv, pnpm, taskfile, monorepo, pytest, vitest, react, typescript, vite, ruff, supply-chain]

# Dependency graph
requires: []
provides:
  - uv Python workspace root (members = libs/*, services/*) with dev group pytest+ruff
  - five shared-lib members (veridoc-audit/crypto/pseudonym/auth/tenancy) + reference-service member, all importable
  - pnpm workspace (apps/*) + React/TS web scaffold (Vite) with a passing Vitest smoke test
  - Taskfile (go-task) glue: install / lint / test:unit / test / build targets
  - Wave 0 test harness — task test:unit runs pytest + vitest green from a clean clone
  - committed lockfiles (uv.lock, pnpm-lock.yaml) + .tool-versions toolchain pins
  - docs/validation/PACKAGE-LEGITIMACY.md (approved supply-chain gate) + VALIDATION-PLAN.md (GAMP 5 test map)
affects: [01-02-audit-sdk, 01-03-crypto-pseudonym, 01-04-auth-tenancy, 01-05-reference-service, 01-06-ci-kind-deploy]

# Tech tracking
tech-stack:
  added: [uv 0.11.20, go-task 3.51.1, pytest, ruff, pnpm 9.15.0, vite 6, vitest 2, react 19, typescript 5, "@testing-library/react", jsdom]
  patterns:
    - "Per-language monorepo (uv + pnpm) glued by a Taskfile — D-08, no Nx/Turborepo"
    - "src/ layout per lib member; import names veridoc_audit etc.; hatchling build backend"
    - "Every third-party install gated by a committed package-legitimacy table (T-01-SC)"
    - "Lockfiles + .tool-versions committed to pin dependency + toolchain versions (T-01-01)"

key-files:
  created:
    - pyproject.toml
    - pnpm-workspace.yaml
    - package.json
    - Taskfile.yml
    - vitest.config.ts
    - .gitignore
    - .tool-versions
    - libs/veridoc-audit/pyproject.toml
    - libs/veridoc-crypto/pyproject.toml
    - libs/veridoc-pseudonym/pyproject.toml
    - libs/veridoc-auth/pyproject.toml
    - libs/veridoc-tenancy/pyproject.toml
    - services/reference-service/pyproject.toml
    - apps/web/package.json
    - apps/web/src/App.tsx
    - apps/web/src/App.test.tsx
    - libs/veridoc-audit/tests/test_smoke.py
    - docs/validation/VALIDATION-PLAN.md
    - uv.lock
    - pnpm-lock.yaml
  modified:
    - docs/validation/PACKAGE-LEGITIMACY.md

key-decisions:
  - "uv chosen over Poetry (D-08 allows either); go-task chosen over GNU Make for the cross-language glue"
  - "Root vitest.config.ts pins test.root to apps/web so React deps resolve under the package boundary while the config lives at the repo root per plan layout"
  - "Member packages use the hatchling build backend with src/ layout; root pyproject is a non-package workspace coordinator (tool.uv.package = false)"
  - "rfc8785 confirmed authentic (Trail of Bits) in Task 1 — no in-house JCS fallback; the package will be installed in plan 01-02"

patterns-established:
  - "Pattern: uv workspace member = pyproject.toml + src/<pkg>/__init__.py + tests/ — downstream plans drop real code into these ready-made members"
  - "Pattern: task test:unit is the fast Wave 0 sampling command (pytest + vitest, no cluster); task test extends with integration later"
  - "Pattern: supply-chain gate — no uv add / pnpm add until PACKAGE-LEGITIMACY.md verdict is APPROVED"

requirements-completed: [PLAT-01]

# Metrics
duration: ~25min
completed: 2026-06-11
---

# Phase 01 Plan 01: Platform Skeleton & Test Harness Summary

**Greenfield VeriDoc monorepo bootstrapped from nothing: a uv Python workspace (5 shared libs + reference service) and a pnpm React/TS workspace glued by a Taskfile, with a green pytest+Vitest Wave 0 harness and a committed package-legitimacy supply-chain gate.**

## Performance

- **Duration:** ~25 min (Tasks 2–3; Task 1 was the human-verify gate, approved separately)
- **Started:** 2026-06-10T21:21Z (executor resume)
- **Completed:** 2026-06-10T21:46Z
- **Tasks:** 3 (Task 1 = approved checkpoint; Tasks 2 & 3 = auto)
- **Files modified:** 44 source/config files (+ lockfiles), excluding .planning bookkeeping

## Accomplishments

- uv workspace root resolves all six members (`uv sync --all-packages` exit 0); all five `veridoc_*` packages import without error.
- pnpm workspace + Vite React/TS scaffold with a passing `App.test.tsx` smoke test.
- `task install`, `task lint`, and `task test:unit` all green from a clean clone — `test:unit` runs **both** pytest (2 passed) and Vitest (1 passed).
- Toolchain (uv, go-task) installed and pinned in `.tool-versions`; `uv.lock` and `pnpm-lock.yaml` committed (T-01-SC / T-01-01).
- `docs/validation/VALIDATION-PLAN.md` maps all four Success Criteria to their automated test commands as the GAMP 5 validation-ready backbone.

## Task Commits

1. **Task 1: Package-legitimacy review gate** — `c55d2f2` (doc creation) + `a3e9545` (approval). All packages APPROVED; rfc8785 adjudicated authentic (Trail of Bits).
2. **Task 2: uv + pnpm workspace roots, lib/service skeleton, Taskfile** — `80a292d` (feat)
3. **Task 3: pytest + Vitest harness and React/TS web scaffold** — `1f1ff54` (feat)

**Plan metadata:** committed separately with this SUMMARY + STATE.md + ROADMAP.md updates.

## Files Created/Modified

- `pyproject.toml` — uv workspace root (`members = ["libs/*", "services/*"]`), dev group pytest+ruff, `[tool.pytest.ini_options]`, ruff config.
- `libs/veridoc-*/pyproject.toml` (×5) + `src/<pkg>/__init__.py` + `tests/` — shared platform lib members (audit/crypto/pseudonym/auth/tenancy).
- `services/reference-service/pyproject.toml` — workspace member depending on all five libs.
- `pnpm-workspace.yaml`, `package.json` — pnpm workspace root + root devDeps (vitest, @vitejs/plugin-react) so the root config resolves.
- `Taskfile.yml` — install / lint / test:unit / test / build (the D-08 cross-language glue).
- `vitest.config.ts` — jsdom + @testing-library/react; `test.root` pinned to apps/web.
- `apps/web/*` — Vite react-ts scaffold + `App.test.tsx` smoke test + `test-setup.ts` (jest-dom).
- `libs/veridoc-audit/tests/test_smoke.py` — placeholder so `uv run pytest` collects ≥1 test.
- `.gitignore`, `.tool-versions`, `README.md` (root + per-member).
- `uv.lock`, `pnpm-lock.yaml` — committed lockfiles.
- `docs/validation/VALIDATION-PLAN.md` — Success-Criterion → test-command map.

## Decisions Made

- **uv + go-task** chosen for the per-language monorepo glue (D-08 permitted uv-or-Poetry and Taskfile-or-Make).
- **Root `vitest.config.ts` with `test.root = apps/web`** — reconciles the plan's "root vitest config" requirement with pnpm's package-scoped React deps (see Deviations / Issues).
- **hatchling + src/ layout** for member packages; root pyproject is a non-package coordinator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed the missing `uv` and `go-task` toolchain**
- **Found during:** Task 2 (workspace setup)
- **Issue:** `uv` and `task` (go-task) were absent on the build host (anticipated in RESEARCH Pitfall 6); `uv sync` / `task lint` could not run.
- **Fix:** Installed `uv` 0.11.20 (astral.sh installer) and `go-task` 3.51.1 (taskfile.dev installer) into `~/.local/bin` (already on PATH). These are the APPROVED toolchain components pinned in `.tool-versions`. No package-manager *library* installs were substituted — only the workspace tooling itself.
- **Verification:** `uv --version`, `task --version` succeed; `task install/lint/test:unit` all exit 0.
- **Committed in:** tooling is host-level (not committed); the pins it enables are in `.tool-versions` (80a292d).

**2. [Rule 3 - Blocking] Root Vitest config could not resolve React deps across the pnpm package boundary**
- **Found during:** Task 3 (test harness wiring)
- **Issue:** A repo-root `vitest.config.ts` (required by the plan) initially failed — `vitest`/`@vitejs/plugin-react` and `react/jsx-dev-runtime` were scoped under `apps/web/node_modules`, not the repo root, so config load and JSX transform both failed.
- **Fix:** Added `vitest` + `@vitejs/plugin-react` to the root `package.json` devDependencies (so the config loads), and pinned `test.root` to `apps/web` in `vitest.config.ts` (so React module resolution + the include glob resolve under the package). The web package's `test`/`vitest` scripts point at the root config via `--config ../../vitest.config.ts`.
- **Verification:** `task test:unit` → Vitest 1 passed; pytest 2 passed; overall exit 0.
- **Committed in:** 1f1ff54 (Task 3 commit).

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking).
**Impact on plan:** Both were prerequisites to satisfy the plan's own verification commands. No scope creep; no package substitutions; all installs remained within the APPROVED legitimacy table.

## Issues Encountered

- Vitest root-config resolution under pnpm (documented as Deviation 2) required two iterations (root devDeps, then `test.root` pinning) before `task test:unit` went green. Resolved within the task.
- pnpm emitted a non-blocking update notice (9.15.0 → 11.x) and one deprecated transitive (`whatwg-encoding`) — out of scope, not actioned.

## Known Stubs

The five `veridoc_*` lib packages and `reference_service` ship as **intentional skeletons** (empty `__init__.py` with docstrings pointing to the implementing plan) — this is the explicit purpose of plan 01-01 per D-07 (ready-made workspace members for plans 02–05 to fill). `libs/veridoc-audit/tests/test_smoke.py` is a placeholder so `uv run pytest` collects ≥1 test; real audit/crypto/pseudonym/service tests land in plans 01-02 … 01-05. These stubs do not block the plan goal (a buildable/testable empty monorepo) and are tracked in `docs/validation/VALIDATION-PLAN.md`.

## User Setup Required

None — no external service configuration required for this scaffold. (Local devs need `uv` and `go-task` on PATH; `.tool-versions` documents the pins, and asdf/mise will pick them up automatically.)

## Next Phase Readiness

- Workspace members are ready for code: plan 01-02 (veridoc-audit / rfc8785 JCS + hash chain), 01-03 (crypto + pseudonym), 01-04 (auth + tenancy), 01-05 (reference-service), 01-06 (CI + kind deploy).
- The Wave 0 harness is green; downstream plans extend `task test` with integration targets (testcontainers Postgres/Redis, Keycloak realm-import) and add `.github/workflows/ci.yml`.
- rfc8785 is APPROVED + authentic — plan 01-02 installs the package (no in-house JCS fallback needed).

## Self-Check: PASSED

All 20 declared key-files verified present on disk; both task commits (`80a292d`, `1f1ff54`) verified in git history. `task install`, `task lint`, and `task test:unit` all exit 0 from a clean workspace.

---
*Phase: 01-platform-skeleton-audit-foundation*
*Completed: 2026-06-11*
