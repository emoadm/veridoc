# Phase 1: Platform Skeleton & Audit Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 1-Platform Skeleton & Audit Foundation
**Areas discussed:** Identity (build vs buy), Audit tamper-evidence design, Walking-skeleton breadth, PII encryption & pseudonymization, Monorepo tooling, Deploy/CI target, Datastore breadth

---

## Identity: build vs buy

| Option | Description | Selected |
|--------|-------------|----------|
| Self-hosted Keycloak | OSS, in-cluster, provider-portable; OIDC/SAML, MFA, RBAC, multi-realm tenancy; self-owned validation evidence | ✓ |
| Cloud-managed IdP (Cognito / Azure AD B2C) | Less ops, but ties identity to a cloud before DEC-cloud-provider is decided; complicates portability + China isolation | |
| Custom identity service | Max control over Part 11 e-sig semantics, but rebuilds MFA/session security from scratch — high effort + validation surface | |

**User's choice:** Self-hosted Keycloak (recommended)
**Notes:** Portability mandate (DEC-cloud-provider open) was the deciding factor.

---

## Audit tamper-evidence design

| Option | Description | Selected |
|--------|-------------|----------|
| Hash-chain in Postgres, synchronous shared lib | Each record hashes prev + payload; append-only, tamper detectable; action + audit commit together | ✓ |
| Hash-chain + async event stream | Stream (Kafka/outbox) chained by audit service; scales better but eventual consistency risks lost/in-flight audit writes | |
| Merkle-batched + external anchoring | Strongest non-repudiation, but heavy/over-engineered for a single-cluster milestone | |

**User's choice:** Hash-chain in Postgres, synchronous shared library (recommended)
**Notes:** Synchronous write chosen specifically to avoid an action succeeding without its audit record.

---

## Walking-skeleton breadth

| Option | Description | Selected |
|--------|-------------|----------|
| Thin walking skeleton | One reference service wired end-to-end + shared platform libs (audit SDK, auth middleware, tenancy) that later phases clone | ✓ |
| Full microservice fleet stubs | Scaffold all eventual services now; more structure but idle stubs + premature boundaries | |

**User's choice:** Thin walking skeleton (recommended)
**Notes:** Prove cross-cutting concerns once; keep Phase 1 focused/verifiable.

---

## PII encryption & pseudonymization

| Option | Description | Selected |
|--------|-------------|----------|
| App-level envelope + deterministic tokens | KMS/HSM-abstracted field encryption; deterministic per-patient pseudonyms for cross-source matching; erasure via key/token deletion | ✓ |
| App-level envelope + random tokens | Stronger unlinkability but needs a separate secured re-identification map | |
| DB-level (pgcrypto) | Simpler app code but couples crypto to Postgres, weaker key isolation, harder to extend to Mongo/blob | |

**User's choice:** App-level envelope encryption + deterministic pseudonym tokens (recommended)
**Notes:** Deterministic tokens chosen because later SDV requires consistent cross-source patient mapping.

---

## Monorepo tooling

| Option | Description | Selected |
|--------|-------------|----------|
| Lightweight, per-language | uv/Poetry (Python) + pnpm (JS) + Makefile/Taskfile + shared CI | ✓ |
| Nx / Turborepo | Unified task graph/caching, but heavier and JS-centric over Python | |

**User's choice:** Lightweight, per-language (recommended)

---

## Deploy/CI target

| Option | Description | Selected |
|--------|-------------|----------|
| kind/k3d + GitHub Actions | Local K8s via same manifests; CI deploys to ephemeral kind cluster — proves deploy path, provider-portable | ✓ |
| docker-compose local, manifests unvalidated | Faster loop but Success Criterion #1 (deploy to K8s via CI) not truly proven | |

**User's choice:** kind/k3d + GitHub Actions (recommended)

---

## Datastore breadth

| Option | Description | Selected |
|--------|-------------|----------|
| Postgres + Redis only | Postgres (audit/identity/tenancy) + Redis (sessions); defer Mongo/blob to phases that need them | ✓ |
| All four now | Stand up Postgres + Mongo + Redis + blob immediately; more complete but idle infra | |

**User's choice:** Postgres + Redis only (recommended)

---

## Claude's Discretion

- Reference-service framework details, repo directory layout, Helm chart structure, CI job decomposition.
- Specific KMS-abstraction library and envelope-encryption key hierarchy.
- Canonical-payload serialization format for the audit hash (must be deterministic).

## Deferred Ideas

- MongoDB document store + blob store → phase that first needs them (Phase 2).
- Real managed cloud cluster + multi-region rollout → gated on DEC-cloud-provider.
- External Merkle anchoring / timestamping notarization of audit log → future hardening.
- Async audit event stream (Kafka/outbox) → revisit only if sync writes bottleneck.
- Full IQ/OQ/PQ validation execution → gates commercial deployment, not this build.
