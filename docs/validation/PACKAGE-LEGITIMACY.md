# Package Legitimacy Audit — Phase 01 (Platform Skeleton & Audit Foundation)

> **Status: AWAITING HUMAN REVIEW.** This document gates every `uv add` / `pnpm add`
> in Phase 01 (threat **T-01-SC** — supply-chain / hallucinated dependency).
> No package may be installed until its row carries an explicit **APPROVED** verdict.
>
> Source: `01-RESEARCH.md` § Package Legitimacy Audit + § Standard Stack. Every package
> there is tagged `[ASSUMED]` because slopcheck, `ctx7`, and registry CLIs
> (`pip index versions`, `npm view`) were network-blocked during the research session.
> The human reviewer must, for each row: (1) confirm the package exists and is the
> authentic, maintained project on the correct registry (not a typo-squat / hallucination),
> (2) confirm the latest stable version, and (3) write the **Verified version** and the
> **Verdict** (`APPROVED` or `REJECTED`).

## How to complete this review

For each row below:

1. Visit the registry URL (`https://pypi.org/project/<name>/` for PyPI,
   `https://npmjs.com/package/<name>` for npm).
2. Confirm it is the authentic, maintained project — check the source repo link,
   maintainer, download counts, and recent release activity. Reject typo-squats / slop.
3. Record the current latest-stable version under **Verified version**.
4. Set **Verdict** to `APPROVED` or `REJECTED` (no blank verdicts permitted).
5. For **rfc8785** specifically, record either `authentic — approved` OR
   `fallback: in-house JCS in plan 02` (see the adjudication note below the tables).

Reply **"approved"** to the executor once every verdict is filled in, or list the
packages to reject / substitute.

---

## Python packages (registry: PyPI)

| Package | Ecosystem / registry | Assumed version | Verified version | Verdict (APPROVED/REJECTED) | Notes |
|---------|----------------------|-----------------|------------------|------------------------------|-------|
| fastapi | PyPI | latest stable | _(to verify)_ | _(to fill)_ | Reference-service HTTP framework. |
| uvicorn | PyPI | latest stable (`uvicorn[standard]`) | _(to verify)_ | _(to fill)_ | ASGI server for FastAPI. |
| pydantic | PyPI | v2.x | _(to verify)_ | _(to fill)_ | Request/response + config validation (V5). |
| pydantic-settings | PyPI | latest stable | _(to verify)_ | _(to fill)_ | Settings/config loading alongside Pydantic v2. |
| sqlalchemy | PyPI | 2.x | _(to verify)_ | _(to fill)_ | ORM / DB access to Postgres (typed 2.x API). |
| alembic | PyPI | latest stable | _(to verify)_ | _(to fill)_ | DB migrations (audit/identity/tenancy schema). |
| psycopg | PyPI | v3 (`psycopg[binary]`) | _(to verify)_ | _(to fill)_ | Modern Postgres driver (sync + async). |
| pyjwt | PyPI | latest stable | _(to verify)_ | _(to fill)_ | JWT signature verification against Keycloak JWKS. |
| jwcrypto | PyPI | latest stable | _(to verify)_ | _(to fill)_ | JWK/JWKS handling for token validation. |
| aws-encryption-sdk | PyPI | 4.x (keyrings/MPL) | _(to verify)_ | _(to fill)_ | Envelope-encryption abstraction (D-11). AWS-official source repo `aws/aws-encryption-sdk-python` — high-trust. Adjudicate vs Tink in plan 01-03. |
| tink | PyPI | latest stable | _(to verify)_ | _(to fill)_ | **Alternative** to aws-encryption-sdk for D-11 (Google-official). Only one of {aws-encryption-sdk, tink} is installed; choice locked in plan 01-03. |
| rfc8785 | PyPI | latest stable | _(to verify)_ | _(to fill — see adjudication)_ | **[SUS] — niche/small package (RESEARCH A4).** RFC 8785 JCS canonicalizer for the audit hash payload. Must be individually adjudicated: verify source-repo authenticity OR fall back to an in-house JCS implementation (decided in plan 01-02). |
| redis | PyPI | 7.x client | _(to verify)_ | _(to fill)_ | Session store client (D-10). |
| pytest | PyPI | latest stable | _(to verify)_ | _(to fill)_ | Python test framework (Wave 0 harness, dev dependency). |
| ruff | PyPI | latest stable | _(to verify)_ | _(to fill)_ | Linter/formatter (dev dependency; `task lint`). |
| testcontainers | PyPI | latest stable | _(to verify)_ | _(to fill)_ | Ephemeral Postgres/Redis for integration tests (dev dependency). |

> **Deferred to later plans, NOT installed in this scaffold plan (listed for review continuity):**
> `fastapi-keycloak-middleware` / `authlib` (OIDC glue — plan 01-04, verify maintenance
> activity before adopting). Add their verified versions + verdicts when those plans run.

## JavaScript / TypeScript packages (registry: npm)

| Package | Ecosystem / registry | Assumed version | Verified version | Verdict (APPROVED/REJECTED) | Notes |
|---------|----------------------|-----------------|------------------|------------------------------|-------|
| vite | npm | latest stable | _(to verify)_ | _(to fill)_ | Build tool / dev server for the React-TS scaffold. |
| react | npm | 18.x or 19.x | _(to verify)_ | _(to fill)_ | Frontend framework (skeleton only this phase). |
| react-dom | npm | matches react | _(to verify)_ | _(to fill)_ | React DOM renderer. |
| typescript | npm | 5.x | _(to verify)_ | _(to fill)_ | TypeScript compiler. |
| vitest | npm | latest stable | _(to verify)_ | _(to fill)_ | JS/TS test framework (Wave 0 harness). |
| @testing-library/react | npm | latest stable | _(to verify)_ | _(to fill)_ | Component testing utilities for the smoke test. |

> **Vite-template transitive scaffolding** (`@vitejs/plugin-react`, `jsdom`,
> `@types/react`, `@types/react-dom`, `@testing-library/jest-dom`) is pulled in by the
> Vite `react-ts` template + Vitest setup. Confirm each is the authentic package at install
> time; record any that you wish to pin/adjudicate explicitly here.

## Container images (not registry packages — recorded for completeness)

| Image | Registry | Version | Verified? | Verdict | Notes |
|-------|----------|---------|-----------|---------|-------|
| keycloak | quay.io / keycloak.org | 26.6.2 | ✅ verified via official keycloak.org release post (May 2026) | APPROVED | OCI image, not a language package; not subject to slopcheck. |

---

## rfc8785 — individual adjudication (RESEARCH A4 / Open Question #4)

`rfc8785` is a niche / small package and is the one row that must be adjudicated on its
own merits. The deterministic JSON canonicalization it provides feeds the audit hash, so
its authenticity is security-relevant (a subtle canonicalization bug → false tamper
positives).

**Reviewer must choose ONE and record it in the rfc8785 Verdict cell above:**

- **`authentic — approved`** — the PyPI `rfc8785` package was verified as the genuine,
  maintained RFC 8785 JCS implementation (source repo + author confirmed). It will be
  installed and guarded by the golden-vector test `test_jcs_golden.py`.
- **`fallback: in-house JCS in plan 02`** — the package could not be verified as
  authentic. Do **not** install it; plan 01-02 implements JCS in-house from the RFC 8785
  spec (small, self-contained), guarded by the same golden-vector test.

Either path is acceptable; the decision is recorded here and consumed by plan 01-02.

---

## Review sign-off

- **Reviewer:** _(name / handle)_
- **Date:** _(YYYY-MM-DD)_
- **Outcome:** _(all APPROVED | rejections listed below)_
- **Rejections / substitutions:** _(none, or list package → action)_

Until this sign-off is complete and the executor receives **"approved"**, no
`uv add` / `pnpm add` (Tasks 2–3 of plan 01-01) may run.
