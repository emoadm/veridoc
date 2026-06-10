# Package Legitimacy Audit — Phase 01 (Platform Skeleton & Audit Foundation)

> **Status: APPROVED (2026-06-11).** This document gates every `uv add` / `pnpm add`
> in Phase 01 (threat **T-01-SC** — supply-chain / hallucinated dependency).
> All rows carry an explicit **APPROVED** verdict; installs may proceed (latest stable,
> pinned via committed lockfiles). `rfc8785` adjudicated **authentic — approved**
> (Trail of Bits, `github.com/trailofbits/rfc8785.py`).
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
| fastapi | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | Reference-service HTTP framework. Well-known authentic project. |
| uvicorn | PyPI | latest stable (`uvicorn[standard]`) | latest stable (lockfile-pinned) | APPROVED | ASGI server for FastAPI. |
| pydantic | PyPI | v2.x | latest 2.x (lockfile-pinned) | APPROVED | Request/response + config validation (V5). |
| pydantic-settings | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | Settings/config loading alongside Pydantic v2. |
| sqlalchemy | PyPI | 2.x | latest 2.x (lockfile-pinned) | APPROVED | ORM / DB access to Postgres (typed 2.x API). |
| alembic | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | DB migrations (audit/identity/tenancy schema). |
| psycopg | PyPI | v3 (`psycopg[binary]`) | latest v3 (lockfile-pinned) | APPROVED | Modern Postgres driver (sync + async). |
| pyjwt | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | JWT signature verification against Keycloak JWKS. Installed as `pyjwt[crypto]` (RS256 needs `cryptography`). |
| jwcrypto | PyPI | latest stable | 1.5.7 (registry-confirmed) | APPROVED | JWK/JWKS handling. Authentic: `github.com/latchset/jwcrypto` (Red Hat). |
| cryptography | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | **Required transitive dependency** of the APPROVED `pyjwt[crypto]` and `jwcrypto` — provides RSA primitives for RS256 JWKS signature verification. Authentic: **PyCA** (Python Cryptographic Authority), `github.com/pyca/cryptography`, the de-facto Python crypto library. Added at plan 01-04 (auth) per the decision-context directive: a needed package not yet in the table is recorded with a verified verdict before install. |
| aws-encryption-sdk | PyPI | 4.x (keyrings/MPL) | latest 4.x (lockfile-pinned) | APPROVED | Envelope-encryption abstraction (D-11). AWS-official `aws/aws-encryption-sdk-python`. Adjudicate vs Tink in plan 01-03. |
| tink | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | **Alternative** to aws-encryption-sdk for D-11 (Google-official). Only one of {aws-encryption-sdk, tink} is installed; choice locked in plan 01-03. |
| rfc8785 | PyPI | latest stable | 0.1.4 (registry-confirmed) | APPROVED (authentic) | RFC 8785 JCS canonicalizer for the audit hash payload. **Adjudicated authentic — approved:** published by **Trail of Bits**, `github.com/trailofbits/rfc8785.py`, Apache-2.0, "pure-Python, no-dependency RFC 8785 JCS." In-house fallback NOT needed. |
| redis | PyPI | 7.x client | latest stable (lockfile-pinned) | APPROVED | Session store client (D-10). |
| pytest | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | Python test framework (Wave 0 harness, dev dependency). |
| ruff | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | Linter/formatter (dev dependency; `task lint`). |
| testcontainers | PyPI | latest stable | latest stable (lockfile-pinned) | APPROVED | Ephemeral Postgres/Redis for integration tests (dev dependency). |

> **Deferred to later plans, NOT installed in this scaffold plan (listed for review continuity):**
> `fastapi-keycloak-middleware` / `authlib` (OIDC glue — plan 01-04, verify maintenance
> activity before adopting). Add their verified versions + verdicts when those plans run.
>
> **Plan 01-04 OIDC-glue resolution (2026-06-11):** No new OIDC-middleware package was
> adopted. `veridoc-auth` verifies Keycloak JWTs directly with the already-APPROVED
> `pyjwt[crypto]` + `jwcrypto` (per the decision-context preference for pyjwt+jwcrypto over
> an unlisted OIDC-glue package). `fastapi-keycloak-middleware` and `authlib` remain
> **NOT installed**. The only newly-installed package is `cryptography` (row added above) —
> the authentic PyCA transitive dependency that `pyjwt[crypto]`/`jwcrypto` require for RS256.

## JavaScript / TypeScript packages (registry: npm)

| Package | Ecosystem / registry | Assumed version | Verified version | Verdict (APPROVED/REJECTED) | Notes |
|---------|----------------------|-----------------|------------------|------------------------------|-------|
| vite | npm | latest stable | latest stable (lockfile-pinned) | APPROVED | Build tool / dev server for the React-TS scaffold. |
| react | npm | 18.x or 19.x | latest stable (lockfile-pinned) | APPROVED | Frontend framework (skeleton only this phase). |
| react-dom | npm | matches react | matches react (lockfile-pinned) | APPROVED | React DOM renderer. |
| typescript | npm | 5.x | latest 5.x (lockfile-pinned) | APPROVED | TypeScript compiler. |
| vitest | npm | latest stable | latest stable (lockfile-pinned) | APPROVED | JS/TS test framework (Wave 0 harness). |
| @testing-library/react | npm | latest stable | latest stable (lockfile-pinned) | APPROVED | Component testing utilities for the smoke test. |

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

- **Reviewer:** emoadm@gmail.com (with Claude diligence: rfc8785 + jwcrypto verified against PyPI)
- **Date:** 2026-06-11
- **Outcome:** all APPROVED
- **Rejections / substitutions:** none. rfc8785 adjudicated `authentic — approved` (Trail of Bits); in-house JCS fallback not required.

Sign-off complete; executor received **"approved"**. Tasks 2–3 of plan 01-01
(`uv add` / `pnpm add` of APPROVED packages) may run. Versions resolve to latest
stable and are pinned via committed lockfiles (`uv.lock`, `pnpm-lock.yaml`).
