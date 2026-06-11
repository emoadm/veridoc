---
phase: 01-platform-skeleton-audit-foundation
plan: 06
subsystem: deploy-ci
tags: [helm, kind, terraform, github-actions, ci, deploy-path, tamper-detection, phase-gate, secrets-contract, threat-model, stride, asvs, gamp5, d-09, plat-01, provider-portable]

# Dependency graph
requires:
  - 01-01 uv + pnpm workspaces, Taskfile (lint/test/build targets extended here with deploy:kind)
  - 01-02 veridoc_audit (test_tamper_detection.py::test_mutated_row_breaks_chain — THE phase gate; audit_log migration applied by the conftest)
  - 01-04 deploy/keycloak/veridoc-realm.json (realm-as-code imported by the Keycloak chart) + the 8 roles + OIDC client
  - 01-05 services/reference-service/Dockerfile (image CI builds + kind-loads) + reference-service integration suite
provides:
  - "deploy/helm/veridoc — provider-portable Helm chart (Keycloak realm-import, Postgres, Redis, reference service) with secret-by-name references"
  - "deploy/helm/veridoc/values-region-eu.yaml — design-only regional-residency overlay (DEC-regional-data-residency)"
  - "deploy/terraform — thin provider-agnostic IaC module (main.tf, variables.tf, README) documenting the portable-IaC posture"
  - "docs/validation/SECRETS-CONTRACT.md — every secret enumerated, sourced, delivered as a K8s Secret never committed (T-06-01)"
  - ".github/workflows/ci.yml — lint / test-unit / integration / deploy-kind (REAL helm install into ephemeral kind + tamper-detection phase gate)"
  - "Taskfile deploy:kind / deploy:kind:down — the deploy path reused by CI and local devs"
  - "docs/validation/THREAT-MODEL.md — consolidated Phase-1 STRIDE register (incl. supply-chain), ASVS L1, block-on-HIGH (GAMP-5 evidence)"
affects: [02-fhir-r4-model-emr-ingestion]

# Tech tracking
tech-stack:
  added: ["Helm chart (v2 apiVersion)", "kind (CI)", "Terraform (thin module, design-only)", "GitHub Actions CI"]
  patterns:
    - "D-09 provider-portable deploy: Helm + kind, NO cloud-specific resources (DEC-cloud-provider OPEN); a thin Terraform module documents the IaC seam without binding a provider"
    - "Real deploy proof, never mocked (RESEARCH Anti-Pattern): CI does a REAL `helm install` into an EPHEMERAL kind cluster + `kubectl wait`, not `--dry-run`"
    - "The deploy:kind Taskfile target is the single source of truth for the deploy path — CI installs the kind binary (install_only) and runs the SAME target a local dev runs"
    - "Secrets are referenced BY NAME in the chart and created out-of-band with EPHEMERAL values (`openssl rand`) in CI — no secret bytes ever in git (T-06-01)"
    - "Keycloak realm-as-code is delivered as a ConfigMap built from deploy/keycloak/veridoc-realm.json and imported with `start-dev --import-realm` (Pitfall 4)"
    - "The tamper-detection gate runs against the DEPLOYED Postgres (port-forward + VERIDOC_TEST_DATABASE_URL), proving the audit immutability property on the real deployed stack, not a local DB"
    - "Pinned action versions (checkout/setup-uv/setup-node/pnpm/setup-helm/kind-action/setup-task)"

key-files:
  created:
    - deploy/helm/veridoc/Chart.yaml
    - deploy/helm/veridoc/values.yaml
    - deploy/helm/veridoc/values-region-eu.yaml
    - deploy/helm/veridoc/templates/_helpers.tpl
    - deploy/helm/veridoc/templates/postgres.yaml
    - deploy/helm/veridoc/templates/redis.yaml
    - deploy/helm/veridoc/templates/keycloak.yaml
    - deploy/helm/veridoc/templates/reference-service.yaml
    - deploy/helm/veridoc/templates/secrets.yaml
    - deploy/terraform/main.tf
    - deploy/terraform/variables.tf
    - deploy/terraform/README.md
    - docs/validation/SECRETS-CONTRACT.md
    - .github/workflows/ci.yml
    - docs/validation/THREAT-MODEL.md
  modified:
    - Taskfile.yml
    - .gitignore
    - deploy/keycloak/veridoc-realm.json
    - libs/veridoc-audit/tests/conftest.py
    - services/reference-service/tests/conftest.py

key-decisions:
  - "CI installs the kind binary via helm/kind-action install_only and runs `task deploy:kind` (which creates its own ephemeral cluster) so the deploy path is exactly the one local devs run — no CI-only deploy logic to drift"
  - "The integration job is Python-only (`uv sync --all-packages`), not the full `task install`, so it needs no pnpm/Node setup"
  - "_normalize_url in both DB conftests forces psycopg v3 for ANY postgresql[+psycopg2]:// URL — testcontainers hands back a +psycopg2 URL that must not load the uninstalled psycopg2"
  - "The realm-as-code JSON must be pure realm representation — Keycloak rejects unknown fields, so the _comment_* documentation keys were stripped (rationale lives in RBAC-MATRIX.md and the plan docs)"

requirements-completed: [PLAT-01]

# Metrics
duration: ~1 day (incl. CI iteration)
completed: 2026-06-11
---

# Phase 01 Plan 06: Provider-Portable Deploy Path + CI Tamper-Detection Gate Summary

**The deploy path proven for real (PLAT-01, Success Criterion #1): a provider-portable Helm chart deploys Keycloak (realm-imported), Postgres, Redis, and the reference service into ONE Kubernetes cluster, a thin Terraform module documents the portable-IaC seam (real managed cluster deferred until DEC-cloud-provider), and a GitHub Actions pipeline lints → unit-tests → integration-tests → builds the reference-service image → spins an EPHEMERAL kind cluster → does a REAL `helm install` (never `--dry-run`) → `kubectl wait`s for readiness → runs the tamper-detection test (`test_mutated_row_breaks_chain`) against the DEPLOYED Postgres as the phase gate → tears down. The deploy is genuinely exercised in CI, so the "mocking the deploy" anti-pattern is closed, and the audit-immutability property (Success Criterion #2) is proven on the real deployed stack. Every secret is referenced by name and injected as an ephemeral K8s Secret — no secret bytes in git (T-06-01). The full pipeline is green in GitHub Actions.**

## Performance

- **Duration:** ~1 day including CI iteration (the build host has no docker/kind/helm, so CI is the authoritative deploy proof — every fix below was surfaced by a real kind deploy).
- **Completed:** 2026-06-11
- **Tasks:** 3 (Task 1 & 2 auto; Task 3 human-verify checkpoint — approved on a green Actions run).
- **Files:** 15 created, 5 modified.

## Accomplishments

- **Provider-portable Helm chart (D-09, Task 1):** `deploy/helm/veridoc` with Chart.yaml, values.yaml (image refs, replica/resource defaults, `region` value), and templates for postgres, redis, keycloak (`start-dev --import-realm` of the mounted realm ConfigMap), reference-service (Deployment + Service, `/healthz` readiness probe), and secrets (named K8s Secret references, **no plaintext values**). `values-region-eu.yaml` is a design-only residency overlay. `helm lint` clean; `helm template` renders all four workloads.
- **Thin Terraform module (Task 1):** `deploy/terraform/` (main.tf, variables.tf, README) documents the provider-agnostic IaC posture — a real managed cluster is deferred until DEC-cloud-provider, but the portable seam exists and is version-controlled.
- **Secrets contract (Task 1):** `docs/validation/SECRETS-CONTRACT.md` enumerates every secret (Keycloak admin, Postgres/Redis creds, Keycloak client secret, KMS master key), where it comes from, and that it is delivered as a K8s Secret never committed (T-06-01).
- **GitHub Actions CI (Task 2):** `.github/workflows/ci.yml` with four jobs — `lint` (ruff + pnpm), `test-unit` (pytest + vitest), `integration` (DB-backed pytest via testcontainers), and `deploy-kind` (build + kind-load the image → `task deploy:kind` real helm install → `kubectl wait` → tamper-detection gate → teardown). Action versions pinned.
- **deploy:kind Taskfile target (Task 2):** creates an ephemeral kind cluster, builds + kind-loads the reference-service image, creates the named Secrets with **ephemeral** `openssl rand` values, builds the realm ConfigMap from the committed realm JSON, does the REAL `helm upgrade --install`, and waits for Postgres/Keycloak/reference-service readiness. Reused verbatim by CI and local devs; `deploy:kind:down` tears the cluster down.
- **Consolidated threat model (Task 2):** `docs/validation/THREAT-MODEL.md` rolls the per-plan STRIDE registers (T-01..T-05 + supply-chain T-01-SC + the T-06 deploy threats) into one Phase-1 model — ASVS L1, block-on-HIGH, no open HIGH threats — as GAMP-5 validation evidence (DEC-gamp5-csv).
- **The phase gate is green for real (Task 3):** the full Actions run is green; in `deploy-kind`, the kind cluster comes up, the image is loaded, `helm install` succeeds, `kubectl wait` reports Postgres/Keycloak/reference-service Ready, and `test_mutated_row_breaks_chain` passes against the deployed Postgres (a mutated audit row breaks the hash chain → `verify_chain` flips False). Real deploy (Success Criterion #1) + tamper detection (Success Criterion #2) both demonstrated in CI.

## Task Commits

1. **Task 1 — Helm chart + Terraform + secrets contract:** `aa61264` `feat(01-06)` — chart (Keycloak/Postgres/Redis/reference-service/secrets templates + values + EU overlay), thin Terraform module, SECRETS-CONTRACT.md.
2. **Task 2 — CI + deploy:kind + threat model:** `a0f52c5` `feat(01-06)` — `.github/workflows/ci.yml`, Taskfile `deploy:kind`/`deploy:kind:down`, THREAT-MODEL.md.
3. **Task 3 — green-CI verification:** approved on a green GitHub Actions run of `emoadm/veridoc` (commit `18eb39f`); the deploy-kind job shows a real helm install into kind + kubectl wait Ready + the tamper-detection test passing.

**CI-iteration fixes (all surfaced by the real kind deploy — see Deviations):** `2616ceb`, `97c80c7`, `d6bfd1a`, `18eb39f`.

**Plan metadata:** this SUMMARY + STATE.md + ROADMAP.md updates committed separately.

## Verification

- **Full GitHub Actions pipeline green** (lint, test-unit, integration, deploy-kind) — the authoritative proof (build host lacks docker/kind/helm).
- `deploy-kind` job: `kind create cluster` ✓, image built + `kind load` ✓, **real** `helm install` (no `--dry-run`) ✓, `kubectl wait` Postgres + Keycloak + reference-service Ready ✓, `test_mutated_row_breaks_chain` passed against the deployed Postgres ✓, cluster torn down ✓.
- Task 2 automated verify: `ci.yml` is valid YAML and contains a kind-creating, image-building, `helm install`, `kubectl wait`, tamper-running job.
- Task 1 automated verify: `helm lint` exits 0; `helm template` renders the reference-service; no plaintext secrets in `secrets.yaml`.
- `helm template` confirmed Keycloak imports `veridoc-realm.json`; reference-service template has a `/healthz` readiness probe.

## Decisions Made

- **CI runs the same `task deploy:kind` a local dev runs** (kind binary via `install_only`, the task creates its own cluster) — no CI-only deploy path that can drift from reality.
- **Integration job is Python-only** (`uv sync --all-packages`) so it needs no pnpm/Node — the JS workspace isn't exercised by the DB-backed tests.
- **`_normalize_url` forces psycopg v3 for any `postgresql[+psycopg2]://` URL** so testcontainers' default `+psycopg2` URL doesn't try to load the uninstalled psycopg2 driver.
- **Realm-as-code JSON is pure `RealmRepresentation`** — Keycloak rejects unknown fields, so the `_comment_*` documentation keys were removed (rationale preserved in RBAC-MATRIX.md and plan docs).

## Deviations from Plan

The plan's Task 3 (run CI and confirm green) surfaced four latent defects that only a **real** deploy could expose — exactly the value of the no-mock deploy gate (RESEARCH Anti-Pattern "mocking the deploy in CI"). All were fixed in-plan.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Integration CI job missing pnpm → `task install` exit 127**
- **Found during:** Task 3 (first CI run).
- **Issue:** The `integration` job ran `task install` (which calls `pnpm install`) but had no pnpm/Node setup → `pnpm: executable file not found`.
- **Fix:** The integration tests are Python-only, so the job now runs `uv sync --all-packages` instead of the full workspace install.
- **Commit:** `2616ceb`.

**2. [Rule 3 - Blocking] testcontainers Postgres URL loaded the uninstalled psycopg2 driver**
- **Found during:** Task 3 (test-unit on CI, where Docker is present).
- **Issue:** On a Docker-equipped runner the DB-backed audit/reference-service tests take the testcontainers path; `get_connection_url()` returns a `postgresql+psycopg2://` URL, but `_normalize_url` only rewrote the bare `postgresql://` prefix → `ModuleNotFoundError: psycopg2`. Off-CI (no Docker) these tests skip, so it was invisible until now.
- **Fix:** `_normalize_url` in both `libs/veridoc-audit/tests/conftest.py` and `services/reference-service/tests/conftest.py` now forces `postgresql+psycopg://` for any `postgresql[+psycopg2]://` URL.
- **Commit:** `97c80c7`.

**3. [Rule 3 - Blocking] Keycloak crashlooped on realm import (unknown-field rejection)**
- **Found during:** Task 3 (deploy-kind — `helm --wait` timed out).
- **Issue:** `start-dev --import-realm` aborted with `Unrecognized field "_comment_roles" ... not marked as ignorable`. The realm JSON carried `_comment_*` documentation keys; Keycloak's `RealmRepresentation` deserializer rejects unknown fields, so Keycloak never became Ready and stalled the whole deploy (Postgres/Redis/reference-service were all Ready).
- **Fix:** Stripped every `_comment*` key from `deploy/keycloak/veridoc-realm.json` (parse + re-serialize to keep valid JSON and key order); realm/roles/client/secret-placeholder all preserved.
- **Commit:** `18eb39f`.

**4. [Rule 4 - Diagnostics] Deploy failures were opaque**
- **Found during:** Task 3 (first `helm --wait` timeout gave no per-pod cause).
- **Issue:** `helm --wait` reports only `context deadline exceeded`, not which pod stalled.
- **Fix:** Added an `if: failure()` step to `deploy-kind` that dumps pod status, namespace events, `kubectl describe`, and current+previous logs for every deployment — this is what pinpointed the Keycloak import error in one run.
- **Commit:** `d6bfd1a`.

**Total deviations:** 4 (3 blocking, 1 diagnostics-hardening). No architectural changes; no scope creep. All fixes are in the deploy/CI/test-harness layer; the chart's application topology and the realm's roles/client are unchanged.

## Issues Encountered

- Postgres logs show recurring `FATAL: role "root" does not exist` connection attempts during the deploy wait. The Postgres pod is Ready and the tamper gate (which connects as `veridoc`) passes, so this is non-blocking noise (a probe/connector defaulting to the OS user), but it's logged here for plan-02 hygiene — worth pinning the connecting user or silencing the probe.

## Known Stubs

- **Terraform is design-only:** the module documents the provider-portable IaC seam but provisions no real managed cluster (DEC-cloud-provider OPEN). The real deploy proof this milestone is kind-in-CI.
- **`values-region-eu.yaml`** is a residency overlay proving the architecture supports regional isolation; no multi-region rollout this milestone (DEC-regional-data-residency design-only).
- **Keycloak runs `start-dev`** (embedded H2) for kind/CI; a production overlay (`start`, configured hostname + TLS, external DB) is deferred hardening.

## Threat Flags

None open. T-06-01..04 are all `mitigate`: secrets are name-referenced + ephemeral (no git bytes), the deploy is a real helm install (not dry-run), the tamper-detection test gates the pipeline against the deployed stack, and the realm is imported as code. The consolidated THREAT-MODEL.md confirms no open HIGH threats across Phase 1 (ASVS L1, block-on-HIGH).

## Next Plan Readiness

- Phase 1 is complete: the platform skeleton, hash-chained audit foundation, identity/RBAC, PII protection, and the **proven** deploy path all exist and are green in CI.
- Phase 2 (FHIR R4 Model & EMR Ingestion) clones the D-07 reference-service path for its own entities and deploys through this same chart + CI gate; the deploy:kind target and the tamper-detection phase gate are now the template every later phase inherits.

## Self-Check: PASSED

All 15 declared created files verified present; the 6 `01-06` commits (`aa61264`, `a0f52c5`, `2616ceb`, `97c80c7`, `d6bfd1a`, `18eb39f`) verified in git history. `ci.yml` valid YAML with the kind/helm-install/kubectl-wait/tamper job; realm JSON valid and free of `_comment*` keys; `_normalize_url` forces psycopg v3 in both conftests. The full GitHub Actions pipeline is green, including the real kind deploy + tamper-detection phase gate (Task 3 human-verify approved).

---
*Phase: 01-platform-skeleton-audit-foundation*
*Completed: 2026-06-11*
