# Phase 1: Platform Skeleton & Audit Foundation - Research

**Researched:** 2026-06-11
**Domain:** Cloud-native regulated platform scaffold (Python/React monorepo), tamper-evident audit trail, Keycloak RBAC/MFA, app-level envelope encryption + deterministic pseudonymization, local-Kubernetes CI/CD
**Confidence:** HIGH (architecture + patterns); MEDIUM (exact library pins — slopcheck/ctx7/registry verification unavailable this session, see Package Legitimacy Audit)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Identity & access (PLAT-03)**
- **D-01:** Identity is **self-hosted Keycloak**, run in-cluster — not a cloud-managed IdP and not a custom identity service. Chosen for provider-portability (DEC-cloud-provider open), native OIDC/SAML + MFA + fine-grained RBAC, multi-realm multi-tenancy, self-owned deployment/validation evidence (CSV/Part 11).
- **D-02:** The 8 roles (CRA, Data Manager, Medical Monitor, Site Coordinator, PI, Sponsor Rep, Regulatory Affairs, System Admin) modeled in Keycloak with distinct access levels. MFA, session management, IP-allowlisting hooks wired in.
- **D-03:** Multi-site / multi-study tenancy represented in the data layer and carried as request-scoped tenancy context (Keycloak realms/claims + app-side tenancy middleware).

**Audit trail (PLAT-02)**
- **D-04:** Tamper-evidence is a **per-record hash chain in Postgres**: each record stores `hash(prev_hash + canonical_payload)`. Append-only; tampering detectable by re-walking the chain. NOT Merkle-batched, NOT external anchoring.
- **D-05:** Services write through a **shared audit SDK, synchronously** — business action and audit record commit together (ideally same transaction). No async event stream this milestone.
- **D-06:** Records capture identity, role, timestamp, action, before/after values; schema also carries **AI-agent decision + confidence fields** (consumed later); supports **15-year append-only** retention.

**Platform scaffold (PLAT-01)**
- **D-07:** Build a **thin walking skeleton** — ONE reference service wired end-to-end (HTTP → authn/authz via Keycloak → audit SDK → Postgres) plus **shared platform libraries** later phases clone.
- **D-08:** **Lightweight, per-language monorepo tooling** — uv or Poetry (Python) + pnpm (React/TS), tied by Makefile/Taskfile + shared CI. No Nx/Turborepo.
- **D-09:** **Deploy/CI target = local Kubernetes (kind or k3d) + GitHub Actions.** CI deploys into an ephemeral kind cluster to prove the deploy path (Success Criterion #1). IaC (Terraform/Helm) provider-portable. No cloud account.
- **D-10:** **Stand up Postgres + Redis only** (Postgres = audit chain/identity/tenancy; Redis = sessions). MongoDB + blob store deferred.

**PII protection (PLAT-03, Success Criterion #4)**
- **D-11:** Field-level PII encryption = **app-level envelope encryption** behind a KMS/HSM abstraction (portable AWS KMS / Azure Key Vault). NOT pgcrypto.
- **D-12:** Pseudonymization = **deterministic per-patient tokens** (same patient maps consistently across EMR/Rave). Right-to-erasure (GDPR Art. 9/17) via **key/token deletion**, not a separate re-identification lookup table.

### Claude's Discretion
- Reference-service framework/language details, repo directory layout, Helm chart structure, CI job decomposition (consistent with the decisions above).
- Specific KMS-abstraction library and envelope-encryption key hierarchy.
- Canonical-payload serialization format for the audit hash (must be stable/deterministic).

### Deferred Ideas (OUT OF SCOPE)
- MongoDB document store + blob store (Phase 2 ingestion/OCR).
- Real managed cloud cluster + multi-region rollout (gated on DEC-cloud-provider).
- External Merkle anchoring / timestamping-authority notarization of the audit log.
- Async audit event stream (Kafka/outbox).
- Full IQ/OQ/PQ validation **execution** (validation-*ready* docs are produced; PQ gates commercial deploy, not this build).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **PLAT-01** | Monorepo + cloud-native service scaffold, provider-portable IaC, CI/CD green (lint/test/build/deploy). Architecture supports regional isolation w/o multi-region rollout. | Standard Stack (monorepo tooling, FastAPI ref service, Helm/Terraform), Architecture Patterns (repo layout, walking skeleton), Validation Architecture (CI deploys to kind), Environment Availability (kind/helm install needed) |
| **PLAT-02** | Tamper-evident audit-trail infra (21 CFR Part 11-ready). Identity/role/timestamp + before/after; agent decision + confidence; query lifecycle; config changes; all login attempts; append-only/immutable/hash-chained; 15-yr retention. | Architecture Pattern 1 (hash-chain audit SDK), Don't Hand-Roll (canonical JSON via JCS), Code Examples (chain compute + verify), Validation Architecture (tamper-detection test), Security Domain (V7 logging) |
| **PLAT-03** | 8 roles w/ distinct access; MFA, session mgmt, IP-allowlist hooks; multi-site/study tenancy in data layer; field-level PII encryption; AES-256 at rest / TLS 1.3 in transit. | Architecture Pattern 2 (Keycloak OIDC + RBAC middleware), Pattern 3 (tenancy middleware), Pattern 4 (envelope encryption + deterministic pseudonymization), Security Domain (V2/V3/V4/V6) |
</phase_requirements>

## Summary

Phase 1 is a **walking-skeleton + cross-cutting-platform-libs** build for a regulated (21 CFR Part 11 / Annex 11 / GDPR / HIPAA) clinical-trial SDV platform. Every later phase clones the patterns established here, so correctness and cleanliness of the shared libs matter more than feature breadth. All major technology choices are already locked in CONTEXT.md (D-01..D-12); research focuses on **how to implement them well** and on the four discretion areas (ref-service framework, repo layout / Helm / CI decomposition, KMS-abstraction library + key hierarchy, canonical serialization for the hash).

The phase delivers five interlocking pieces: (1) a per-language monorepo (uv-Python + pnpm-TS, glued by Taskfile + GitHub Actions); (2) ONE FastAPI reference service wired HTTP → Keycloak authn/authz → tenancy context → business action → **synchronous, same-transaction** hash-chained audit write → envelope-encrypted Postgres persistence; (3) shared platform libraries (audit SDK, auth/RBAC middleware, tenancy context, crypto/envelope helper, pseudonymization helper) that are independently cloneable; (4) Keycloak in-cluster with 8 roles, MFA, session mgmt, IP-allowlist hooks; (5) provider-portable Helm charts + Terraform that CI installs into an **ephemeral kind cluster** so the deploy path is genuinely proven, not mocked.

The two highest-risk design subtleties — which the planner must resolve explicitly — are: **(a)** the canonical-payload serialization that feeds the audit hash must be byte-deterministic (use RFC 8785 JSON Canonicalization Scheme, not `json.dumps`), and **(b)** D-11 (envelope encryption) and D-12 (deterministic pseudonym + erasure-by-key-deletion) must be designed *together* under a **per-patient key** hierarchy — otherwise deterministic tokens and crypto-shredding are mutually exclusive (deleting a single global key would erase everyone).

**Primary recommendation:** Build a FastAPI (Python 3.12) reference service + SQLAlchemy 2.x/Alembic on Postgres, Keycloak 26.6.x in-cluster for OIDC/RBAC/MFA, a shared audit SDK that computes `SHA-256(prev_hash || JCS(payload))` and commits the audit row in the **same DB transaction** as the business write, and an envelope-encryption helper backed by the **AWS Encryption SDK for Python (keyrings)** or **Google Tink** as the provider-portable KMS abstraction, with a **per-patient data-key** hierarchy that simultaneously enables deterministic pseudonyms and GDPR crypto-shredding. CI installs Helm charts into an ephemeral `kind` cluster and runs a tamper-detection integration test as the phase gate.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Authentication (OIDC, MFA) | Identity (Keycloak, in-cluster) | API (token validation middleware) | Keycloak owns credential/MFA/session; API only validates the resulting JWT — never handles passwords (D-01) |
| Authorization (8-role RBAC) | API / Backend (middleware) | Identity (role claims source) | Roles defined in Keycloak; enforcement is per-request in the API tier (defence-in-depth at the resource boundary) |
| Tenancy scoping (site/study) | API / Backend (request-scoped middleware) | Database (row-level tenancy columns) | Tenancy is a request-context concern; the data layer stores tenancy keys, middleware enforces filtering (D-03) |
| Tamper-evident audit write | API / Backend (shared audit SDK) | Database (append-only table, same txn) | Synchronous, same-transaction write is an application concern; Postgres provides the durable append-only store + constraint triggers (D-04, D-05) |
| Field-level PII encryption | API / Backend (envelope-encrypt before persist) | KMS/HSM (wraps the data key) | App-level envelope encryption keeps plaintext keys out of the DB engine; KMS only wraps/unwraps DEKs (D-11) |
| Deterministic pseudonymization | API / Backend (ingestion-time helper) | KMS (per-patient key custody) | Token derivation is application logic; key custody/erasure lives in KMS so crypto-shredding works (D-12) |
| Session state | Redis | API (session middleware) | Redis is the session store (D-10); Keycloak/API read/write session keys there |
| Deploy / orchestration | Kubernetes (kind locally + CI) | CI (GitHub Actions) | Helm charts are the unit of deploy; CI proves the path in an ephemeral cluster (D-09) |
| Data residency isolation (design-only) | Infrastructure (Helm/Terraform values) | — | Per-region deploy is a values/overlay concern; no multi-region rollout this milestone (DEC-regional-data-residency) |

## Standard Stack

> **Provenance note:** slopcheck, `ctx7`, and registry CLIs (`pip index versions`, `npm view`) were all **unavailable / network-blocked** in this research session. Per the package-legitimacy protocol, every package below is tagged `[ASSUMED]` and the planner MUST gate each install behind a `checkpoint:human-verify` task (confirm latest stable + slopcheck `[OK]` at plan time). Keycloak 26.6.2 version IS verified via web (official keycloak.org release post, May 2026).

### Core
| Library | Version (assume; verify at plan time) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Keycloak** | 26.6.x | Self-hosted IdP: OIDC, MFA, RBAC, multi-realm tenancy | `[VERIFIED: keycloak.org]` 26.6.2 latest stable (May 2026); the de-facto open-source IdP; provider-portable (D-01) |
| **Python** | 3.12.x | Reference-service + shared-lib language | `[VERIFIED: local]` 3.12.3 present; aligns with PROJECT.md (Python backend / LangGraph later) |
| **FastAPI** | latest stable `[ASSUMED]` | Reference-service HTTP framework | Async, OpenAPI-native (validation evidence), Pydantic-typed, mature OIDC middleware ecosystem |
| **Uvicorn** | latest `[ASSUMED]` | ASGI server for FastAPI | Standard FastAPI production server |
| **Pydantic** | v2.x `[ASSUMED]` | Request/response + config validation (V5 input validation) | Standard with FastAPI; settings via `pydantic-settings` |
| **SQLAlchemy** | 2.x `[ASSUMED]` | ORM / DB access to Postgres | 2.x typed API; same-transaction audit write needs explicit session control |
| **Alembic** | latest `[ASSUMED]` | DB migrations (audit/identity/tenancy schema) | Standard SQLAlchemy migration tool; migrations are CSV evidence |
| **psycopg** | v3 `[ASSUMED]` | Postgres driver | Modern driver; sync + async |
| **PostgreSQL** | 16.x `[ASSUMED]` | Audit chain, identity mirror, tenancy | Locked store (D-10); append-only + constraint triggers |
| **Redis** | 7.x `[ASSUMED]` | Session store | Locked store (D-10) |
| **uv** | latest `[ASSUMED]` (NOT installed) | Python workspace + dependency mgmt | D-08 names uv OR Poetry; uv is faster, supports workspaces |
| **pnpm** | 9.x `[VERIFIED: local]` 9.15.0 | JS/TS workspace mgmt | D-08; pnpm workspaces present in env |
| **React + TypeScript** | React 18/19, TS 5.x `[ASSUMED]` | Frontend scaffold (skeleton only this phase) | PROJECT.md mandated; Vite recommended for scaffold |

### Supporting
| Library | Version `[ASSUMED]` | Purpose | When to Use |
|---------|---------|---------|-------------|
| **AWS Encryption SDK for Python** | 4.x (keyrings/MPL) | Envelope encryption abstraction over AWS KMS (+ raw/Azure via keyring) | Primary candidate for D-11 KMS abstraction; 4.x uses keyrings + AEAD |
| **Google Tink (Python)** | latest | Alternative envelope-encryption abstraction; AEAD primitive, KMS-agnostic (AWS/GCP/Azure) | Use if a single library must wrap both AWS KMS + Azure Key Vault with one API |
| **python-jose / PyJWT + jwcrypto** | latest | JWT signature verification against Keycloak JWKS | Token validation in auth middleware (don't trust without sig check) |
| **rfc8785 (JCS canonicalizer)** | latest | RFC 8785 JSON Canonicalization for the audit hash payload | Deterministic serialization (the discretion item) — see Don't Hand-Roll |
| **Authlib** OR **fastapi-keycloak-middleware** | latest | OIDC client/middleware glue | Reduces hand-rolled OIDC; verify maintenance + slopcheck before adopting |
| **Taskfile (go-task)** OR **GNU Make** | latest | Cross-language task runner gluing uv + pnpm | D-08 glue layer |
| **Helm** | 3.x (NOT installed) | Provider-portable K8s packaging | D-09 deploy unit |
| **kind** OR **k3d** | latest (NOT installed) | Local + CI ephemeral K8s | D-09 CI deploy target |
| **Terraform** | latest (NOT installed) | Provider-portable IaC (thin this phase) | D-09; keep provider-agnostic modules |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI | Django REST / Flask | FastAPI's async + OpenAPI + Pydantic typing fit a validation-evidence + later-async-agent platform better; Django heavier than a walking skeleton needs |
| AWS Encryption SDK | Google Tink | Tink is more cloud-agnostic out of the box (one API for AWS/Azure/GCP); AWS Enc SDK is AWS-first but supports raw/custom keyrings. **Either satisfies D-11** — pick by which gives cleaner Azure Key Vault parity |
| uv | Poetry | D-08 permits both; Poetry more mature/established, uv faster + single-binary. Recommend **uv** (workspace + speed) but Poetry is a safe fallback |
| kind | k3d | Both run K8s-in-Docker; kind is the CNCF-standard for CI ephemeral clusters with first-class GitHub Action; k3d (k3s) is lighter. Recommend **kind** for CI parity |
| RFC 8785 JCS | Protobuf canonical / CBOR deterministic | JCS keeps payloads human-readable JSON (audit-review friendly, Annex 11) while being byte-deterministic; binary formats lose reviewability |
| Hash chain in app | Postgres trigger-computed chain | App-side keeps the canonicalization logic testable + portable; triggers risk diverging canonicalization. Recommend **app-side compute, DB-enforced append-only** |

**Installation (illustrative — pin exact versions at plan time after slopcheck):**
```bash
# Python ref service + shared libs (uv workspace)
uv add fastapi uvicorn[standard] pydantic pydantic-settings sqlalchemy alembic "psycopg[binary]" \
       pyjwt jwcrypto aws-encryption-sdk rfc8785 redis
# Frontend scaffold (pnpm workspace)
pnpm create vite@latest web -- --template react-ts
# Tooling not yet on this machine — install before planning execution:
#   uv, helm, kind (or k3d), kubectl, terraform, docker, go-task
```

## Package Legitimacy Audit

> slopcheck was **NOT available** in this session (pip install failed). Per protocol, all installed packages are `[ASSUMED]` and the planner MUST insert a `checkpoint:human-verify` task before each `uv add` / `pnpm add` that confirms (1) latest stable version, (2) slopcheck `[OK]`, (3) correct ecosystem registry (PyPI for Python, npm for JS).

| Package | Registry | Verified this session? | slopcheck | Disposition |
|---------|----------|------------------------|-----------|-------------|
| keycloak (container image) | quay.io / keycloak.org | ✅ 26.6.2 via official release post | n/a (OCI image) | Approved |
| fastapi | PyPI | ✗ registry blocked | not run | `[ASSUMED]` — gate at plan time |
| uvicorn | PyPI | ✗ | not run | `[ASSUMED]` — gate |
| pydantic / pydantic-settings | PyPI | ✗ | not run | `[ASSUMED]` — gate |
| sqlalchemy / alembic | PyPI | ✗ | not run | `[ASSUMED]` — gate |
| psycopg | PyPI | ✗ | not run | `[ASSUMED]` — gate |
| pyjwt / jwcrypto | PyPI | ✗ | not run | `[ASSUMED]` — gate |
| aws-encryption-sdk | PyPI | ✗ (GitHub `aws/aws-encryption-sdk-python` is the authoritative source repo) | not run | `[ASSUMED]` — gate; high-trust (AWS-official repo) |
| tink (alternative) | PyPI | ✗ (Google-official) | not run | `[ASSUMED]` — gate |
| rfc8785 | PyPI | ✗ | not run | `[ASSUMED]` — **gate carefully**: small/niche package, verify source repo + author before adopting; alternative is a vetted in-house JCS implementation |
| fastapi-keycloak-middleware / authlib | PyPI | ✗ | not run | `[ASSUMED]` — gate; verify maintenance activity |
| redis (py) | PyPI | ✗ | not run | `[ASSUMED]` — gate |
| react / typescript / vite | npm | ✗ npm view blocked | not run | `[ASSUMED]` — gate |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck could not run).
**Packages flagged as suspicious [SUS]:** `rfc8785` flagged by reviewer judgement (niche/small — verify source repo authenticity, or implement JCS in-house from RFC 8785 spec). No automated SUS verdicts available.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────────────────────────────┐
   HTTPS (TLS1.3)   │              kind / K8s cluster              │
  ┌──────────────►  │                                              │
  │  React/TS web   │   ┌────────────┐    OIDC discovery/JWKS      │
  │  (skeleton)     │   │  Keycloak  │◄──────────────┐             │
  └──────────────►  │   │ 8 realms/  │               │             │
                    │   │ roles, MFA │               │             │
                    │   └─────┬──────┘               │             │
   Authenticated    │         │ access token (JWT)   │             │
   request ────────►│   ┌─────▼───────────────────────────────┐   │
                    │   │      FastAPI REFERENCE SERVICE       │   │
                    │   │  ┌────────────────────────────────┐ │   │
                    │   │  │ 1. AuthN middleware  (verify   │ │   │
                    │   │  │    JWT sig vs JWKS, MFA acr)   │ │   │
                    │   │  │ 2. RBAC middleware  (8 roles)  │ │   │
                    │   │  │ 3. Tenancy middleware          │ │   │
                    │   │  │    (site/study from claims)    │ │   │
                    │   │  └──────────────┬─────────────────┘ │   │
                    │   │   business handler                   │   │
                    │   │        │                             │   │
                    │   │   ┌────▼─────────────────────────┐   │   │
                    │   │   │  SHARED PLATFORM LIBS        │   │   │
                    │   │   │  • crypto: envelope-encrypt  │   │   │
                    │   │   │    PII (per-patient DEK)─────┼───┼──►│ KMS / HSM
                    │   │   │  • pseudonym: deterministic  │   │   │ (AWS KMS /
                    │   │   │    token (per-patient key)   │   │   │  Azure KV;
                    │   │   │  • audit SDK: JCS(payload),  │   │   │  abstracted)
                    │   │   │    SHA256(prev||payload)     │   │   │
                    │   │   └────┬───────────────┬─────────┘   │   │
                    │   │        │ SAME DB TXN   │             │   │
                    │   └────────┼───────────────┼─────────────┘   │
                    │      ┌─────▼──────┐  ┌──────▼──────┐          │
                    │      │ PostgreSQL │  │   Redis     │          │
                    │      │ audit chain│  │  sessions   │          │
                    │      │ (append-   │  └─────────────┘          │
                    │      │  only) +   │                           │
                    │      │ identity/  │                           │
                    │      │ tenancy +  │                           │
                    │      │ enc. PII   │                           │
                    │      └────────────┘                           │
                    └──────────────────────────────────────────────┘
   GitHub Actions: lint → test → build images → `kind create cluster`
                 → helm install → integration test (incl. tamper-detection) → teardown
```

The load-bearing invariant: a single business write and its audit record commit in **one Postgres transaction** (D-05). If the audit write fails, the business action rolls back — there is never a business change without its audit row.

### Recommended Project Structure
```
veridoc/
├── Taskfile.yml                  # or Makefile — glues uv + pnpm + helm/kind (D-08)
├── pyproject.toml                # uv workspace root (members = services/* + libs/*)
├── pnpm-workspace.yaml           # pnpm workspace root (apps/web)
├── .github/workflows/ci.yml      # lint/test/build/deploy-to-kind (D-09)
├── libs/                         # SHARED PLATFORM LIBS (cloned by later phases) (D-07)
│   ├── veridoc-audit/            #   audit SDK: JCS + hash chain + same-txn writer
│   ├── veridoc-auth/             #   OIDC verify + 8-role RBAC + IP-allowlist middleware
│   ├── veridoc-tenancy/          #   request-scoped site/study context middleware
│   ├── veridoc-crypto/           #   envelope-encryption helper (KMS abstraction)
│   └── veridoc-pseudonym/        #   deterministic per-patient token + erasure
├── services/
│   └── reference-service/        #   THE one walking-skeleton FastAPI service (D-07)
│       ├── app/ (api, models, migrations[alembic])
│       └── Dockerfile
├── apps/
│   └── web/                      #   React/TS scaffold (Vite)
├── deploy/
│   ├── helm/veridoc/             #   provider-portable Helm chart (D-09)
│   │   ├── templates/ (keycloak, postgres, redis, reference-service)
│   │   └── values.yaml + values-region-*.yaml  # residency-as-overlay (design only)
│   └── terraform/                #   provider-portable modules (thin this phase)
└── docs/validation/             #   URS→FS→DQ + IQ/OQ-ready evidence (GAMP 5, validation-READY)
```

### Pattern 1: Synchronous, same-transaction hash-chained audit write (D-04, D-05, D-06)
**What:** A shared `audit.record(session, event)` helper that, **inside the caller's open DB transaction**, (1) `SELECT … FOR UPDATE` (or serialize on) the latest chain head to read `prev_hash`, (2) canonicalizes the payload via JCS (RFC 8785), (3) computes `SHA-256(prev_hash || canonical_payload)`, (4) inserts the append-only row. Because it shares the business transaction, audit + business commit atomically.
**When to use:** Every state-changing action and every login attempt (success+failure), config change, data read/modify/delete with before/after.
**Concurrency note:** Serialize chain-head reads (advisory lock or `SERIALIZABLE` isolation on the audit table head) so two concurrent writers can't fork the chain. This is the #1 correctness trap — see Pitfall 1.
**Schema must include now** (avoid migrating an append-only table later, per D-06): `id`, `prev_hash`, `record_hash`, `actor_id`, `actor_role`, `tenant_id` (site/study), `action`, `entity_type`, `entity_id`, `before` (jsonb), `after` (jsonb), `agent_decision` (jsonb, nullable — for Phase 4), `agent_confidence` (numeric, nullable), `occurred_at` (tz), `created_at` (tz, server default).
**Append-only enforcement:** a `BEFORE UPDATE OR DELETE` trigger that raises, plus least-privilege grants (the app role has INSERT/SELECT only). Belt-and-suspenders for Part 11 immutability.

### Pattern 2: OIDC authn + 8-role RBAC middleware (D-01, D-02)
**What:** Auth middleware fetches Keycloak's JWKS (cached), verifies the access-token signature + `iss`/`aud`/`exp`, asserts the MFA `acr`/`amr` claim is present, then exposes the principal + roles to the request. RBAC middleware/decorator checks the route's required role against the token's realm/client roles.
**When to use:** Every protected route. The reference service demonstrates it once; later services import `veridoc-auth`.
**Key point:** The API tier NEVER handles passwords or MFA — Keycloak owns that (D-01). The service only validates JWTs. IP-allowlisting is a hook (middleware checkpoint reading an allowlist per site/tenant), wired but data-driven.

### Pattern 3: Request-scoped tenancy context (D-03)
**What:** Tenancy middleware extracts `site`/`study` claims (mapped from Keycloak realm/claims) into a request-scoped context (e.g., `contextvars`); the data layer reads that context to scope every query (tenant_id filter) and stamp every audit row. No query may run without a resolved tenant context (fail-closed).

### Pattern 4: Envelope encryption + deterministic pseudonymization under a per-patient key hierarchy (D-11, D-12) — **CRITICAL DESIGN**
**What:** A **per-patient root key** lives in / is wrapped by KMS. From it derive: (a) the **pseudonym token** = deterministic `HMAC(patient_key, patient_natural_id)` (stable across EMR + Rave → cross-source matching), and (b) per-field **data keys (DEKs)** used to AES-256-GCM encrypt PII fields (envelope encryption — DEK wrapped by the patient/KMS key, stored alongside ciphertext).
**Why together:** D-12 says erasure = key/token **deletion**. If the pseudonym used one *global* key, deleting it would break every patient. The reconciling pattern (confirmed by crypto-shredding literature) is **per-patient key isolation**: erasing patient X destroys only X's key → X's ciphertext becomes unrecoverable AND X's deterministic token can no longer be recomputed = GDPR Art. 17 satisfied **without** deleting rows (preserves the 15-yr append-only audit trail). This is the single most important thing for the planner to get right.
**When to use:** At ingestion (Phase 2 consumes it) and anywhere PII is written. Phase 1 proves the helper end-to-end in the reference service against synthetic patient data.

### Anti-Patterns to Avoid
- **`json.dumps` for the hash payload:** non-deterministic key order / whitespace / float formatting → false tamper positives. Use JCS (RFC 8785).
- **Async/eventual audit writes:** explicitly forbidden this milestone (D-05) — risks a committed business action with an in-flight (or lost) audit row.
- **pgcrypto / DB-engine encryption for PII:** forbidden (D-11) — puts keys in the DB engine and doesn't extend to Mongo/blob.
- **Global pseudonym key:** breaks GDPR crypto-shredding (see Pattern 4).
- **Heavyweight monorepo orchestrator (Nx/Turborepo):** forbidden (D-08).
- **Mocking the deploy in CI:** Success Criterion #1 requires a real `helm install` into a real (ephemeral kind) cluster, not a dry-run.
- **Trusting a JWT without JWKS signature verification:** classic auth bypass.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Identity / MFA / sessions / SAML / OIDC | Custom auth service | **Keycloak** (D-01) | Auth is a minefield; Keycloak gives Part 11-relevant MFA/session/audit out of the box |
| Deterministic JSON serialization | Hand-rolled key-sort + float formatting | **RFC 8785 JCS** library (or a small, fully-tested in-house impl of the RFC) | Float/Unicode/key-order edge cases are exactly where DIY canonicalization breaks → false tamper alerts |
| Envelope encryption (DEK gen, wrap/unwrap, AEAD) | Custom AES + KMS calls | **AWS Encryption SDK (keyrings)** or **Tink** | Nonce reuse / AAD / key-wrapping mistakes are catastrophic; these libs implement AEAD envelope encryption correctly |
| JWT verification | Manual base64 + signature math | **PyJWT / jwcrypto** against Keycloak JWKS | Signature/`alg`-confusion bugs cause auth bypass |
| DB migrations of an append-only table | Ad-hoc SQL | **Alembic** + design the agent fields NOW (D-06) | Migrating an immutable table later is painful; anticipate columns |
| Local K8s for CI | Bash + docker-compose pretending to be K8s | **kind** (+ official GitHub Action) | Proves the *actual* Helm/K8s deploy path (Success Criterion #1) |
| Crypto-shredding erasure | Re-identification lookup table + row deletes | **Per-patient key deletion** (D-12) | Key deletion erases without touching the append-only audit trail |

**Key insight:** In a regulated SDV platform, the audit chain, the crypto, and the IdP are precisely the components where a subtle DIY bug is both most likely and most costly (a tampering false-positive, a key-reuse leak, or an auth bypass each invalidates Part 11/GDPR posture). Spend the budget on correctly wiring vetted libraries once, in the shared libs, so every later phase inherits correctness.

## Runtime State Inventory

> Greenfield phase — most categories are N/A, but this phase *creates* runtime state every later phase inherits.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None pre-existing (greenfield). This phase CREATES: Postgres audit chain (append-only), identity/tenancy tables, encrypted-PII columns; Redis session keys. | Initial Alembic migrations; seed Keycloak realm/roles |
| Live service config | None pre-existing. This phase CREATES: **Keycloak realm export** (8 roles, MFA flows, clients) — this MUST be exported to git as a realm JSON, not left only in Keycloak's DB, or CI/fresh clusters lose it. | Commit Keycloak realm-import JSON to `deploy/`; load via realm import on startup |
| OS-registered state | None (runs in K8s, not host OS). | None |
| Secrets/env vars | None pre-existing. This phase INTRODUCES: KMS credentials/key refs, Keycloak admin creds, Postgres/Redis creds. Must be K8s Secrets, never in git. | Define secret contract (sealed-secrets or values-driven); document for later phases |
| Build artifacts | None pre-existing. This phase CREATES: container images (reference-service, web), Helm chart package. | CI builds + loads images into kind |

**Nothing found to migrate:** Confirmed greenfield — verified by file listing (`.planning/`, `docs/` only; no source tree). All state above is *newly created*, not migrated.

## Common Pitfalls

### Pitfall 1: Forked / racing audit chain under concurrency
**What goes wrong:** Two concurrent requests both read the same `prev_hash`, both compute against it, and insert two rows claiming the same predecessor → the chain forks and verification later fails (or worse, silently accepts).
**Why it happens:** The read-modify-write of the chain head isn't serialized.
**How to avoid:** Serialize chain-head access — a Postgres advisory lock keyed to the chain, or `SERIALIZABLE` isolation, or a single-writer pattern. Because writes are same-transaction (D-05) and this is single-cluster, an advisory lock per audit stream is simple and sufficient.
**Warning signs:** Two audit rows with identical `prev_hash`; intermittent verification failures under load.

### Pitfall 2: Non-deterministic canonical payload
**What goes wrong:** Re-walking the chain reports tampering on untouched records.
**Why it happens:** `json.dumps` key ordering, whitespace, float/`Decimal` formatting, Unicode escaping vary across runs/library versions.
**How to avoid:** RFC 8785 JCS for the payload; pin the canonicalizer; add a golden-vector test (known input → known hash) that fails CI if serialization drifts.
**Warning signs:** Hash mismatches after a dependency bump or across services.

### Pitfall 3: Deterministic pseudonym vs. crypto-shredding collision
**What goes wrong:** Team picks a single global HMAC key for pseudonyms; later GDPR erasure can't delete one patient without breaking all tokens — or they add a re-identification lookup table that D-12 explicitly rejects.
**Why it happens:** D-11 (encryption) and D-12 (pseudonym + erasure) get designed separately.
**How to avoid:** Per-patient key hierarchy (Pattern 4); design both helpers together in `veridoc-crypto` + `veridoc-pseudonym`.
**Warning signs:** A `patient_pseudonym_map` table appears; erasure stories require row deletes from append-only tables.

### Pitfall 4: Keycloak realm config not in version control
**What goes wrong:** CI spins a fresh Keycloak with no roles/clients/MFA; the deploy "passes" but auth is unconfigured; later devs can't reproduce the realm.
**Why it happens:** Realm config edited in the Keycloak admin UI lives only in Keycloak's DB.
**How to avoid:** Export realm to JSON, commit it, import on startup (Keycloak `--import-realm`). Treat realm config as code (Annex 11 change control).
**Warning signs:** "Works on my cluster"; manual UI steps in the runbook.

### Pitfall 5: Audit row commits in a separate transaction
**What goes wrong:** Business write commits, audit write fails → an unrecorded action (Part 11 violation), or vice-versa.
**Why it happens:** Audit SDK opens its own session/transaction instead of joining the caller's.
**How to avoid:** Audit SDK takes the caller's `Session`/connection and inserts within it; no internal commit. Integration test: force the audit insert to fail and assert the business row rolled back.

### Pitfall 6: Tooling absent on the build host
**What goes wrong:** Plans assume uv/helm/kind/docker exist; execution fails.
**Why it happens:** This machine has node/pnpm/python3 but **NOT uv, docker, kind, k3d, kubectl, helm, terraform** (verified this session).
**How to avoid:** Plan an explicit "install toolchain" task (or document GitHub-Actions-only execution for the K8s deploy). See Environment Availability.

## Code Examples

> Illustrative patterns (synthesized from cited approaches; treat as `[ASSUMED]` until library APIs confirmed at plan time).

### Hash-chain compute + append (same transaction)
```python
# Source pattern: RFC 8785 JCS + SHA-256 chain (CITED: dev.to/veritaschain hash-chain guide;
#   appmaster.io tamper-evident PostgreSQL) — adapted to same-transaction write (D-05)
import hashlib, rfc8785  # rfc8785 = JCS; verify package authenticity at plan time

def append_audit(session, payload: dict) -> str:
    # serialize on the chain head (advisory lock) — prevents forks (Pitfall 1)
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": AUDIT_CHAIN_LOCK})
    prev = session.execute(
        text("SELECT record_hash FROM audit_log ORDER BY id DESC LIMIT 1")
    ).scalar() or ""                         # genesis = ""
    canonical = rfc8785.dumps(payload)       # bytes, RFC 8785 deterministic
    record_hash = hashlib.sha256(prev.encode() + canonical).hexdigest()
    session.execute(text(
        "INSERT INTO audit_log (prev_hash, record_hash, payload, ...) "
        "VALUES (:p, :h, :pl, ...)"),
        {"p": prev, "h": record_hash, "pl": canonical.decode(), ...})
    return record_hash                       # NO commit here — caller's txn owns it
```

### Tamper-detection verification (the phase-gate test)
```python
def verify_chain(session) -> bool:
    prev = ""
    for row in session.execute(text(
        "SELECT prev_hash, record_hash, payload FROM audit_log ORDER BY id ASC")):
        if row.prev_hash != prev:
            return False                     # broken link
        recomputed = hashlib.sha256(prev.encode() + row.payload.encode()).hexdigest()
        if recomputed != row.record_hash:
            return False                     # payload tampered
        prev = row.record_hash
    return True
```

### Envelope-encrypt a PII field (per-patient key)
```python
# Source pattern: AWS Encryption SDK for Python keyrings (CITED: github.com/aws/aws-encryption-sdk-python)
# OR Google Tink AEAD (CITED: docs.cloud.google.com/kms/docs/client-side-encryption)
ciphertext, header = client.encrypt(
    source=plaintext_pii.encode(),
    keyring=patient_keyring(patient_id),     # DEK wrapped by per-patient/KMS key
)
# pseudonym (deterministic, per-patient key → crypto-shred by deleting the key)
import hmac, hashlib
token = hmac.new(patient_key, patient_natural_id.encode(), hashlib.sha256).hexdigest()
```

### OIDC JWT validation against Keycloak JWKS
```python
# Source pattern: Keycloak realm discovery + JWKS (CITED: fastapi-keycloak-middleware docs;
#   keycloak.org OIDC). Verify signature, iss/aud/exp, and MFA acr.
claims = jwt.decode(token, jwks_key, algorithms=["RS256"],
                    audience=CLIENT_ID, issuer=f"{KC_URL}/realms/{REALM}")
assert claims.get("acr") in ALLOWED_ACR_FOR_MFA   # enforce MFA was performed
roles = claims["realm_access"]["roles"]            # 8-role RBAC check downstream
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Poetry-only Python deps | **uv** workspaces (Rust-fast resolver, single binary) | 2024–2025 | D-08 permits both; uv now mainstream for monorepos |
| `json.dumps(sort_keys=True)` for canonical hashing | **RFC 8785 JCS** | RFC 8785 (2020), now standard for tamper-evident logs | Avoids float/Unicode edge cases `sort_keys` misses |
| AWS Encryption SDK master-key providers | **Keyrings (SDK 4.x + MPL)** | AWS Enc SDK 4.x | Cleaner multi-key / cross-region envelope model |
| Keycloak WildFly distro | **Keycloak Quarkus distro** (26.x) | since 17+; 26.6.x current | Faster start, container-native; what you'll deploy |
| Re-identification lookup tables for pseudonyms | **Crypto-shredding (per-entity key deletion)** | mainstreamed 2023–2026 for GDPR×retention | D-12's erasure-by-key-deletion is the current best practice |

**Deprecated/outdated:**
- Keycloak WildFly distribution — replaced by Quarkus distribution (use 26.6.x).
- `python-keycloak` brittle admin patterns — prefer realm-import-as-code + standard OIDC JWKS validation.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FastAPI is the right ref-service framework (Python backend implied, not explicitly locked) | Standard Stack | Low — Pydantic/OpenAPI/async fit; Django/Flask viable; affects only ref-service shape |
| A2 | All Python/JS package latest-stable versions (registry CLIs blocked this session) | Standard Stack / Pkg Audit | Medium — wrong pin → install failure; **planner must verify + slopcheck each** |
| A3 | AWS Encryption SDK (keyrings) chosen over Tink for D-11 | Standard Stack / Pattern 4 | Low-Medium — both satisfy D-11; choose by Azure Key Vault parity. **User/planner should confirm** |
| A4 | `rfc8785` PyPI package is authentic/maintained | Don't Hand-Roll / Pkg Audit | Medium — niche package; if unverifiable, implement JCS in-house from the RFC |
| A5 | uv chosen over Poetry (D-08 allows either) | Standard Stack | Low — Poetry is a clean fallback |
| A6 | kind chosen over k3d (D-09 allows either) | Standard Stack | Low — k3d is a clean fallback |
| A7 | Per-patient key hierarchy is the intended reconciliation of D-11+D-12 | Pattern 4 | **High** — if the team intended global keys, GDPR erasure design changes materially. **Confirm with user before locking.** |
| A8 | Advisory-lock single-writer is acceptable for chain serialization at this scale | Pattern 1 / Pitfall 1 | Low-Medium — fine single-cluster; revisit if throughput grows |
| A9 | Synthetic patient data is sufficient to exercise PII/pseudonym paths in Phase 1 | Validation Architecture | Low — milestone is fixture-driven by design |

**These assumptions (esp. A2, A3, A4, A7) should be surfaced to the user/planner before becoming locked decisions.**

## Open Questions (RESOLVED)

> All four questions are resolved via in-plan gating; no further plan changes required. Each item records where/how it was decided.

1. **AWS Encryption SDK vs. Tink for the KMS abstraction (D-11)**
   - What we know: both implement AEAD envelope encryption and abstract KMS; both portable.
   - What's unclear: which gives the cleaner single-API parity across AWS KMS *and* Azure Key Vault (DEC-cloud-provider open).
   - Recommendation: planner picks during design; bias to **Tink** if one library must natively wrap both clouds, else **AWS Encryption SDK** keyrings with a raw-KV keyring for Azure.
   - **RESOLVED:** Decided at plan **01-03 Task 1** (`checkpoint:decision`, blocking) — the chosen library (tink-hkdf or awsenc-hkdf, consistent with PACKAGE-LEGITIMACY.md APPROVED status) is recorded in `docs/validation/KEY-HIERARCHY.md` before Tasks 2/3 begin.

2. **Per-patient key hierarchy confirmation (A7)**
   - What we know: per-patient keys reconcile deterministic pseudonyms (D-12) with crypto-shredding erasure; a global key cannot.
   - What's unclear: whether the team anticipated per-patient KMS key proliferation (cost/quota) vs. per-patient keys *derived* from a master key (HKDF) with erasure via deleting the derivation salt/material.
   - Recommendation: design `veridoc-crypto` around a master-key + per-patient derived key (HKDF) so erasure = delete the patient's derivation material; confirm with user.
   - **RESOLVED:** master key + per-patient **HKDF-derived** keys; a global pseudonym/encryption key is explicitly **rejected** (Pitfall 3). Locked in plan **01-03** (Task 1 decision + Task 2 implementation); erasure = delete the patient's derivation material. Documented in `docs/validation/KEY-HIERARCHY.md`.

3. **Reference-service business action**
   - What we know: D-07 needs ONE service wired end-to-end; the *what* it does is unspecified.
   - Recommendation: pick a thin, representative write (e.g., "register a study site" or "record a synthetic patient") that exercises tenancy + PII encryption + audit in one path.
   - **RESOLVED:** a thin, tenancy-scoped **Subject create/update** (plan **01-05**) — exercises authn → authz → tenancy → envelope-encrypted PII + deterministic pseudonym → same-transaction hash-chained audit in one path, with no later-phase domain logic.

4. **`rfc8785` package authenticity (A4)**
   - Recommendation: if the PyPI package can't be verified (small/niche), implement JCS from RFC 8785 in `veridoc-audit` with golden-vector tests — the spec is small and self-contained.
   - **RESOLVED:** adjudicated in plan **01-02 Task 1** against PACKAGE-LEGITIMACY.md — use the `rfc8785` package if APPROVED, otherwise an **in-house JCS** implementation from RFC 8785, guarded by the committed golden-vector test (`test_jcs_golden.py`).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node | pnpm/React scaffold | ✓ | 22.16.0 | — |
| pnpm | JS/TS workspace (D-08) | ✓ | 9.15.0 | — |
| python3 | ref service + libs | ✓ | 3.12.3 | — |
| uv | Python workspace (D-08) | ✗ | — | Poetry (also absent — must install one) |
| docker | build images + kind backend | ✗ | — | **none — blocking for local K8s**; runs in CI (GitHub Actions has Docker) |
| kind | local + CI ephemeral K8s (D-09) | ✗ | — | k3d (also absent) — install in CI/host |
| k3d | alt local K8s | ✗ | — | kind |
| kubectl | K8s control (D-09) | ✗ | — | none — install |
| helm | deploy unit (D-09) | ✗ | — | raw manifests (worse; D-09 wants Helm) |
| terraform | provider-portable IaC (D-09) | ✗ | — | thin this phase; install before IaC tasks |

**Missing dependencies with no fallback (blocking):**
- **docker, kubectl, kind/k3d, helm** — required to run/prove the K8s deploy locally. Either (a) add a toolchain-install task, or (b) scope the *cluster deploy + tamper-detection integration test* to **GitHub Actions** (which provides Docker), and keep local dev at unit/integration level. Recommendation: do BOTH — install toolchain for local devs AND run the authoritative deploy proof in CI (matches D-09 and Success Criterion #1).

**Missing dependencies with fallback:**
- uv ↔ Poetry; kind ↔ k3d — choose one of each and install.

## Validation Architecture

> nyquist_validation: no `.planning/config.json` found → **treated as ENABLED** (default). Each Success Criterion below is given a provable/automatable test.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | **pytest** (Python services/libs) + **Vitest** (React/TS scaffold) — both `[ASSUMED]`, none configured yet (Wave 0) |
| Config file | none yet — Wave 0 creates `pyproject.toml [tool.pytest]` + `vitest.config.ts` |
| Quick run command | `task test:unit` (uv run pytest -x -q; pnpm vitest run) |
| Full suite command | `task test` (unit + integration incl. kind deploy + tamper-detection) |

### Phase Requirements → Test Map
| Req / Success Criterion | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC#1 / PLAT-01 | Scaffold builds + lints + deploys to a real (kind) cluster green | integration (CI) | `kind create cluster && helm install … && kubectl wait …` in GitHub Actions | ❌ Wave 0 |
| SC#2 / PLAT-02 | Every action → append-only hash-chained record w/ identity/role/ts/before-after | unit + integration | `pytest libs/veridoc-audit/tests/test_chain.py -x` | ❌ Wave 0 |
| SC#2 / PLAT-02 | **Tamper is detectable** — mutate a prior audit row, re-walk chain, expect failure | integration (THE gate) | `pytest …/test_tamper_detection.py::test_mutated_row_breaks_chain -x` | ❌ Wave 0 |
| SC#2 / PLAT-02 | Audit write + business write are atomic (force audit fail → business rolls back) | integration | `pytest …/test_same_txn.py -x` | ❌ Wave 0 |
| SC#2 / PLAT-02 | Canonical serialization is stable (golden vector) | unit | `pytest …/test_jcs_golden.py -x` | ❌ Wave 0 |
| SC#3 / PLAT-03 | Auth with one of 8 roles behind MFA; role sees only permitted access | integration | `pytest …/test_rbac.py` (Keycloak in compose/kind; assert 403 cross-role; assert MFA acr enforced) | ❌ Wave 0 |
| SC#3 / PLAT-03 | All login attempts (success + failure) audited | integration | `pytest …/test_login_audit.py` | ❌ Wave 0 |
| SC#4 / PLAT-03 | PII field-level encrypted at rest (ciphertext in DB, not plaintext) | integration | `pytest …/test_field_encryption.py` (assert raw column ≠ plaintext; decrypt round-trips) | ❌ Wave 0 |
| SC#4 / PLAT-03 | Deterministic pseudonym: same patient → same token across calls | unit | `pytest …/test_pseudonym_deterministic.py` | ❌ Wave 0 |
| SC#4 / PLAT-03 | Erasure: delete patient key → token irrecomputable + ciphertext undecryptable | integration | `pytest …/test_crypto_shred.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `task test:unit` (chain, JCS golden, pseudonym determinism — all fast, no cluster).
- **Per wave merge:** `task test` (adds Keycloak/Postgres integration via docker-compose or kind).
- **Phase gate:** Full suite green in GitHub Actions **including the kind deploy + tamper-detection test** before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `pyproject.toml [tool.pytest]` + `task` targets — no test framework configured yet
- [ ] `vitest.config.ts` for the web scaffold
- [ ] `libs/veridoc-audit/tests/` — chain, tamper-detection, same-txn, JCS golden vector
- [ ] `libs/veridoc-crypto/tests/` + `libs/veridoc-pseudonym/tests/` — encryption round-trip, determinism, crypto-shred
- [ ] `services/reference-service/tests/` — RBAC (Keycloak fixture), login-attempt audit, field-encryption at rest
- [ ] CI workflow `.github/workflows/ci.yml` with kind-action deploy stage
- [ ] Test fixtures: synthetic patient data, ephemeral Postgres/Redis (testcontainers or compose), Keycloak realm-import for tests

## Security Domain

> security_enforcement: no config found → **treated as ENABLED**. This is a 21 CFR Part 11 / Annex 11 / GDPR / HIPAA platform — security is the core deliverable.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture | yes | Documented trust boundaries (diagram above); secrets in K8s Secrets not git; threat model in validation docs |
| V2 Authentication | yes | **Keycloak** OIDC + MFA (D-01/D-02); API validates JWT vs JWKS, never handles credentials |
| V3 Session Management | yes | Keycloak sessions in **Redis** (D-10); session timeout/idle policies; logout invalidation |
| V4 Access Control | yes | 8-role RBAC middleware (D-02); tenancy fail-closed (D-03); IP-allowlist hooks; deny-by-default routes |
| V5 Input Validation | yes | **Pydantic v2** models on all inputs; reject unexpected fields |
| V6 Cryptography | yes | **AES-256-GCM envelope encryption** via AWS Enc SDK / Tink (D-11); KMS-wrapped DEKs; **never hand-roll**; TLS 1.3 in transit |
| V7 Error Handling & Logging | yes | **The hash-chained audit trail** (D-04/05/06) — append-only, tamper-evident; capture all login attempts + config changes; no PII in error messages |
| V8 Data Protection | yes | Field-level PII encryption at rest; pseudonymization at ingestion (D-12); crypto-shredding erasure; 15-yr retention |
| V9 Communications | yes | TLS 1.3 in transit (ingress); mTLS optional intra-cluster |
| V10 Malicious Code | partial | slopcheck-gated dependency installs (see Pkg Audit); pin + lockfiles |
| V12 Files/Resources | n/a this phase | (blob/document store deferred to Phase 2) |
| V13 API | yes | OIDC-protected endpoints; OpenAPI spec as validation evidence; rate-limit hooks |

### Known Threat Patterns for {Python/FastAPI + Keycloak + Postgres + K8s}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Audit-log tampering / deletion | Tampering / Repudiation | Hash chain + append-only trigger + INSERT/SELECT-only DB grant (D-04); re-walk verification test |
| Audit chain fork under concurrency | Tampering | Advisory lock / serialize chain head (Pitfall 1) |
| JWT signature bypass / `alg=none` | Spoofing / Elevation | Verify sig vs JWKS, pin `RS256`, check iss/aud/exp (Code Examples) |
| Cross-tenant data access | Elevation / Info Disclosure | Fail-closed tenancy middleware; tenant_id on every query (D-03) |
| SQL injection | Tampering | SQLAlchemy parameterized queries / ORM — never string-format SQL |
| PII leak at rest | Info Disclosure | Field-level envelope encryption (D-11); ciphertext-in-DB test |
| Encryption-key compromise / non-erasable PII | Info Disclosure / Compliance | KMS-wrapped DEKs out of DB; per-patient key crypto-shredding (D-12) |
| Secrets in image/git | Info Disclosure | K8s Secrets / sealed-secrets; no creds in Helm values committed plaintext |
| MFA bypass | Spoofing | Enforce MFA `acr/amr` claim in auth middleware, not just Keycloak policy |
| Supply-chain (hallucinated/malicious dep) | Tampering | slopcheck + lockfile pin + human-verify checkpoints (Pkg Audit) |

## Project Constraints (from CLAUDE.md)

No `./CLAUDE.md` exists in the repository (verified this session). Binding constraints therefore come from PROJECT.md + constraints.md and are reflected throughout: 21 CFR Part 11 / Annex 11 / GDPR Art. 9&17 / HIPAA baseline from day one; AES-256 at rest, TLS 1.3 in transit; RBAC+MFA+session+IP-allowlist; immutable 15-yr audit; field-level PII encryption; HSM/KMS key management; provider-portable IaC (DEC-cloud-provider open); architecture must *support* regional residency (no rollout); GAMP 5 validation-*ready* docs (no IQ/OQ/PQ execution this phase); coding standards (SNOMED/MedDRA/LOINC/CTCAE/ATC) are later-phase concerns.

## Sources

### Primary (HIGH confidence)
- `docs/prd/veridoc-pid.md` §3.1–3.5 (tech stack, security/compliance), §4.1–4.4 (regulations, CSV, audit, HITL) — sole source spec
- `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/intel/constraints.md` — locked decisions + constraints
- `.planning/phases/01-…/01-CONTEXT.md` — D-01..D-12 locked decisions
- keycloak.org — Keycloak **26.6.2** latest stable (released May 2026): https://www.keycloak.org/2026/05/keycloak-2662-released
- github.com/aws/aws-encryption-sdk-python — AWS Encryption SDK 4.x keyrings (envelope encryption): https://github.com/aws/aws-encryption-sdk-python/
- Google Cloud KMS — Tink client-side/envelope encryption (AEAD): https://docs.cloud.google.com/kms/docs/client-side-encryption
- RFC 8785 — JSON Canonicalization Scheme (deterministic JSON for hashing)

### Secondary (MEDIUM confidence)
- fastapi-keycloak-middleware docs — OIDC/JWKS integration patterns: https://fastapi-keycloak-middleware.readthedocs.io/
- appmaster.io — tamper-evident audit trails in PostgreSQL with hash chaining: https://appmaster.io/blog/tamper-evident-audit-trails-postgresql
- dev.to/veritaschain — SHA-256 hash-chain audit log guide + crypto-shredding for GDPR×retention
- freecodecamp.org — envelope encryption with KMS explainer: https://www.freecodecamp.org/news/envelope-encryption/

### Tertiary (LOW confidence — verify at plan time)
- All Python/JS package versions: registry CLIs (`pip index versions`, `npm view`) and slopcheck were unavailable this session — **planner must verify each + run slopcheck**.
- Medium articles on FastAPI+Keycloak and crypto-shredding (corroborating, not authoritative).

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — choices well-grounded in locked decisions + spec; exact version pins unverified (registry blocked) → all `[ASSUMED]`, Keycloak 26.6.2 the exception (web-verified).
- Architecture: HIGH — patterns are well-established and directly derived from D-01..D-12; hash-chain + same-txn + per-patient-key designs cross-checked against current literature.
- Pitfalls: HIGH — the four critical traps (chain fork, non-deterministic serialization, pseudonym/crypto-shred collision, realm-as-code) are concrete and testable.
- Security/Validation: HIGH — ASVS map + per-Success-Criterion test map are directly actionable for Wave 0.

**Research date:** 2026-06-11
**Valid until:** ~2026-07-11 (30 days; re-verify Keycloak patch level + package versions at plan time since registry checks were deferred)
