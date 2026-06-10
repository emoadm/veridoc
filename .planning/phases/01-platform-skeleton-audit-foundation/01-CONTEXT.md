# Phase 1: Platform Skeleton & Audit Foundation - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a running cloud-native scaffold where every system action is captured in a
tamper-evident, 21 CFR Part 11-ready audit trail, and identity/RBAC exists for the 8
defined user roles — with patient-identifiable data pseudonymized and field-level
encrypted at rest. Concretely: monorepo + one reference service + CI/CD pipeline +
audit-trail infrastructure + RBAC/identity baseline.

The FHIR R4 model and ingestion (Phase 2), Rave mock integration (Phase 3), the agent
fleet (Phases 4–6), and the portal UIs (Phase 7) are OUT of this phase. This phase
builds the cross-cutting foundation those phases stand on.

Locked, NOT re-decided here (project-level):
- **DEC-cloud-provider OPEN** → all IaC/runtime stays AWS/Azure-portable this milestone.
- **DEC-regional-data-residency** → architecture must *support* regional isolation; no
  multi-region rollout now.
- Security baseline binding from day one (21 CFR Part 11 / Annex 11 / GDPR / HIPAA):
  immutable audit + 15-yr retention, RBAC/MFA, AES-256 at rest / TLS 1.3 in transit,
  field-level PII encryption.
</domain>

<decisions>
## Implementation Decisions

### Identity & access (PLAT-03)
- **D-01:** Identity is **self-hosted Keycloak**, run in-cluster — not a cloud-managed
  IdP and not a custom-built identity service. Chosen for provider-portability
  (DEC-cloud-provider is open), native OIDC/SAML + MFA + fine-grained RBAC, multi-realm
  support for multi-tenancy, and self-owned deployment/validation evidence (CSV/Part 11).
- **D-02:** The 8 roles (CRA, Data Manager, Medical Monitor, Site Coordinator, PI,
  Sponsor Rep, Regulatory Affairs, System Admin) are modeled in Keycloak with distinct
  access levels. MFA, session management, and IP-allowlisting hooks are wired in.
- **D-03:** Multi-site / multi-study tenancy is represented in the data layer and
  carried as request-scoped tenancy context (e.g., via Keycloak realms/claims +
  app-side tenancy middleware).

### Audit trail (PLAT-02)
- **D-04:** Tamper-evidence is a **per-record hash chain in Postgres**: each audit
  record stores `hash(prev_hash + canonical_payload)`, making the log append-only and
  tampering with any prior record detectable by re-walking the chain. (Not Merkle-batched,
  not external anchoring — those are over-engineered for a single-cluster milestone.)
- **D-05:** Services write to the audit trail through a **shared audit SDK,
  synchronously**, so a business action and its audit record commit together (ideally in
  the same transaction). No async event stream this milestone — eventual consistency
  would risk an action succeeding while its audit write is in flight.
- **D-06:** Audit records capture identity, role, timestamp, action, and before/after
  values; the schema is designed to also carry AI-agent decision + confidence fields
  (consumed by later phases) and to support 15-year append-only retention.

### Platform scaffold (PLAT-01)
- **D-07:** Build a **thin walking skeleton**, not a full fleet of stubs: ONE reference
  service wired end-to-end (HTTP → authn/authz via Keycloak → audit SDK → Postgres) plus
  **shared platform libraries** (audit SDK, auth/RBAC middleware, tenancy context) that
  later phases clone. Proves every cross-cutting concern exactly once.
- **D-08:** **Monorepo tooling is lightweight and per-language** — uv or Poetry workspace
  for Python, pnpm workspace for React/TS — tied together by a Makefile/Taskfile and
  shared CI. No Nx/Turborepo (heavyweight orchestrator not justified at this scale).
- **D-09:** **Deploy/CI target is local Kubernetes (kind or k3d) + GitHub Actions.**
  Local dev runs on kind/k3d using the same Helm charts/manifests; CI runs
  lint/test/build and deploys into an ephemeral kind cluster in GitHub Actions to truly
  prove the deploy path (Success Criterion #1). No cloud account needed; a real managed
  cluster waits for DEC-cloud-provider. IaC (Terraform/Helm) stays provider-portable.
- **D-10:** **Stand up Postgres + Redis only** in Phase 1 (Postgres = audit chain,
  identity, tenancy; Redis = sessions). MongoDB (document store) and the blob store are
  deferred to the phases that need them (EMR ingestion / OCR).

### PII protection (PLAT-03, Success Criterion #4)
- **D-11:** Field-level PII encryption is **app-level envelope encryption** behind a
  KMS/HSM abstraction (portable across AWS KMS / Azure Key Vault) — not DB-level
  pgcrypto. Keeps keys out of the DB engine and extends cleanly to Mongo/blob later.
- **D-12:** Pseudonymization uses **deterministic per-patient tokens**, so the same
  patient maps consistently across EMR and Rave sources — a prerequisite for later
  cross-source SDV matching. Right-to-erasure (GDPR Art. 9) is handled via key/token
  deletion rather than a separate re-identification lookup table.

### Claude's Discretion
- Exact reference-service framework/language details, repo directory layout, Helm chart
  structure, and CI job decomposition (planner/researcher to choose, consistent with the
  decisions above).
- Specific KMS-abstraction library and envelope-encryption key hierarchy.
- Canonical-payload serialization format used for the audit hash (must be stable/
  deterministic).
</decisions>

<specifics>
## Specific Ideas

- The walking skeleton must demonstrate the full cross-cutting path **once**:
  authenticated request → role check → business action → synchronous tamper-evident
  audit write → encrypted persistence. Later phases reuse the shared libs, not re-invent.
- Keep mock → production and AWS → Azure swaps trivial: identity (Keycloak), crypto
  (KMS abstraction), and IaC (Terraform/Helm) all stay portable.
- Audit schema should anticipate agent decision + confidence fields now, even though no
  agent writes to it until Phase 4, to avoid a later migration of an append-only table.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Primary spec
- `docs/prd/veridoc-pid.md` — VeriDoc AI Project Initiation Document (the sole source
  spec). Sections 3.x = technical architecture (tech stack by layer, regional residency);
  sections 4.x = security & compliance baseline (21 CFR Part 11, Annex 11, GDPR, HIPAA,
  audit-trail requirements, RBAC/MFA, HSM/field-level encryption).

### Project-level decisions & requirements (read for locked constraints)
- `.planning/PROJECT.md` — locked decisions (DEC-cloud-provider open, DEC-regional-data-
  residency), security/compliance baseline, coding standards.
- `.planning/REQUIREMENTS.md` §Platform & Foundation — PLAT-01, PLAT-02, PLAT-03 (the
  acceptance-level detail this phase implements).
- `.planning/intel/constraints.md` — CON-audit-trail, CON-security-compliance,
  CON-data-residency, CON-gamp5-csv (validation-ready posture).

No formal ADRs exist yet (0 ADRs); the PID is embedded-authoritative.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield repository. Only `docs/`, `.planning/`, and the source `.docx` PID
  exist; there is no source tree, monorepo, or service yet. This phase creates the
  scaffold and the shared platform libraries that ALL later phases will reuse.

### Established Patterns
- None in code yet. The patterns this phase *establishes* (and later phases must follow):
  shared audit SDK, auth/RBAC middleware, tenancy context, envelope-encryption helper,
  provider-portable Helm/Terraform.

### Integration Points
- The audit SDK, auth middleware, and tenancy/crypto helpers are the integration seams
  every subsequent phase plugs into. Phase 2 (ingestion) and Phase 3 (Rave) both depend
  only on Phase 1, so the shared libs and the reference-service template must be clean
  enough to clone independently.
</code_context>

<deferred>
## Deferred Ideas

- **MongoDB document store + blob store** — stood up in the phase that first needs them
  (Phase 2 EMR ingestion / OCR DocumentReference), not now.
- **Real managed cloud cluster + multi-region rollout** — gated on DEC-cloud-provider;
  this milestone proves the deploy path on local kind/k3d only.
- **External Merkle anchoring / timestamping-authority notarization** of the audit log —
  a possible future hardening beyond the in-DB hash chain; not needed for single-cluster
  Part 11 readiness.
- **Async audit event stream (Kafka/outbox)** — revisit only if synchronous audit writes
  become a scaling bottleneck in later phases.
- **Full IQ/OQ/PQ validation execution** — validation-*ready* docs are produced; PQ +
  production access gate commercial deployment, not this build (CON-gamp5-csv).
</deferred>

---

*Phase: 01-platform-skeleton-audit-foundation*
*Context gathered: 2026-06-10*
