# VeriDoc AI

AI-powered Source Data Verification (SDV) for clinical trials: a fleet of specialized
agents verifies EMR source data against Medidata Rave eCRF data, with ALCOA+ assessment,
prioritized discrepancy queries, and a tamper-evident audit trail. Decision-support only
(mandatory human-in-the-loop).

## Monorepo layout

Per-language workspaces glued by a Taskfile (D-08, no Nx/Turborepo):

- `pyproject.toml` — uv workspace root (`libs/*` + `services/*`)
- `pnpm-workspace.yaml` — pnpm workspace root (`apps/*`)
- `libs/` — shared platform libraries (D-07): `veridoc-audit`, `veridoc-crypto`,
  `veridoc-pseudonym`, `veridoc-auth`, `veridoc-tenancy`
- `services/reference-service/` — the one walking-skeleton FastAPI service
- `apps/web/` — React/TS scaffold (Vite)
- `docs/validation/` — GAMP 5 validation-ready evidence

## Quick start

```bash
task install     # uv sync + pnpm install
task lint        # ruff + pnpm lint
task test:unit   # pytest + vitest
```

Toolchain pins live in `.tool-versions`. Every third-party install is gated by
`docs/validation/PACKAGE-LEGITIMACY.md` (threat T-01-SC).
