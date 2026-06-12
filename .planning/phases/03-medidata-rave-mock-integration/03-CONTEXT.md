# Phase 3: Medidata Rave Mock Integration - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a **bidirectional MDRWS integration behind an abstraction layer**, exercised
against a **Rave mock**, so the platform can READ eCRF data from and WRITE
discrepancies/flags to Medidata Rave, with the MDRWS contract isolated so a
mock → production swap requires **zero agent-code changes** (Success Criterion #4).

Concretely this phase delivers:
- An abstraction **Port** (ABC) over MDRWS with a single **HTTP adapter** behind it.
- A **Rave mock** = a real FastAPI HTTP server emulating the MDRWS endpoints we use.
- **READ**: subject data, CRF field values (with audit trail), query status, protocol
  deviations, randomization, freeze/lock status — returned as typed Rave DTOs.
- **WRITE**: open discrepancy notes (queries), update query status, set per-field SDV
  flags, flag protocol deviations — against the (stateful) mock.
- **WEBHOOKS**: a real HTTP receiver service that the mock POSTs to (new data entry /
  SAE submission / query response), which dispatches the corresponding pipeline action.

OUT of scope (own phases): the agent fleet / Orchestrator / LLM engine and the
human-in-the-loop gating (Phase 4); SDV / ALCOA+ / Lab / AE-SAE / ConMed / Consistency
agents and the actual FHIR↔eCRF field comparison (Phase 5); Query/Risk/Report agents
and full query-lifecycle automation (Phase 6); portals (Phase 7); production MDRWS
access (deferred — CON-medidata-partner).

Locked, NOT re-decided here (carried from project-level / prior phases):
- **DEC-rave-primary-ecrf** — Medidata Rave (MDRWS) is the primary eCRF target.
- **CON-medidata-partner** — production access is parallel/non-blocking; this phase
  builds against a **mock** behind an abstraction layer.
- **D-05 / PLAT-02** — every query-lifecycle and webhook event writes to the
  `veridoc-audit` SDK in the caller's transaction (immutable, hash-chained audit).
- **D-12 / D-14** — patient-identifiable data is pseudonymized with `veridoc-pseudonym`.
- **DEC-cloud-provider OPEN** — anything deployable stays AWS/Azure-portable.
- **DEC-rq-json-serializer** — RQ jobs use JSONSerializer; event payloads must be
  JSON-serializable primitives (no pickle, no raw bytes).
- **D-07 walking-skeleton** — shared `veridoc-*` libs + thin service(s) cloned from the
  Phase 1/2 reference pattern.

</domain>

<decisions>
## Implementation Decisions

### Abstraction boundary & mock shape
- **D-01:** The abstraction is a **Port (ABC)** over MDRWS with a **single concrete HTTP
  adapter** behind it (mirrors the `SourceAdapter` ABC / `KMSKeyring` idiom from Phase 2).
  The same HTTP adapter is used in tests (pointed at the mock) and in production (pointed
  at real Rave) — so the mock → production swap is a **base-URL/config change only**, and
  the production adapter is already exercised. (Chosen over an in-process Python fake,
  which would leave production HTTP code unexercised at swap time.)
- **D-02:** The **Rave mock is a real FastAPI HTTP server** that answers over the network,
  emulating the MDRWS surface — not an in-process stub.
- **D-03:** The mock emulates the **real MDRWS surface faithfully but scoped to only the
  endpoints we use** (READ/WRITE/webhooks): real RWS URL conventions, HTTP Basic auth, and
  ODM-based error semantics. These endpoints are written down as the **MDRWS contract**
  that the abstraction targets.
- **D-04:** The mock is **stateful** — it persists query/flag/PD state per run in its own
  store, so a discrepancy note can be opened and its status later updated/verified
  end-to-end (makes Success Criterion #2 reproducibly verifiable).

### Data contract representation
- **D-05:** **ODM-XML on the wire** (faithful to MDRWS), but the adapter **parses it into
  typed Pydantic Rave DTOs** at the boundary: `Subject`, `CrfFieldValue` (carrying its
  audit trail), `QueryStatus`, `ProtocolDeviation`, `Randomization`, `FreezeLockStatus`.
  Agents consume clean typed objects; **ODM-XML stays an adapter-internal detail** and is
  never exposed to agents. (Chosen over passing raw ODM through, and over force-mapping
  eCRF into FHIR — eCRF is not naturally FHIR and that mapping would be lossy.)
- **D-06:** The Rave DTOs are a **distinct eCRF model**, separate from the FHIR R4 source
  model (Phase 2). Agents (Phase 5) compare the two sides; the Rave side is NOT normalized
  to FHIR.

### Subject identity & pseudonymization
- **D-07:** The **Rave `Subject` ID is pseudonymized with the same `veridoc-pseudonym`
  mechanism** (D-12/D-14) used at ingestion — consistent GDPR Art. 9 handling and
  validation-ready, even on synthetic data.
- **D-08:** EMR↔Rave correlation (linking a FHIR `Patient` to a Rave `Subject`) is done
  via a **site-level mapping kept OUTSIDE agent code**. Agents receive correlated/typed
  data; they do not implement the linkage themselves.

### Webhook mechanism
- **D-09:** **Real HTTP receiver**: a `rave-integration` service exposes an HTTP webhook
  receiver endpoint; the **mock plays the sender** (POSTs as Rave would). The receiver
  authenticates the request, writes a `veridoc-audit` entry, and enqueues an RQ job.
  (Mirrors the `ingestion-service` FastAPI + RQ pattern; verifiable end-to-end over the
  wire in CI. Chosen over an in-process callback, which wouldn't exercise the real HTTP
  path production needs.)
- **D-10:** **Thin verifiable dispatch (Phase-3 scope):** the receiver maps each event
  type (new data entry / SAE submission / query response) to a **named pipeline action**,
  writes audit, and enqueues a typed RQ job onto a **`rave-events`** queue. A **stub
  consumer** processes it (no-op + `rave:webhook:dispatched` audit) so Success Criterion #3
  is provable now. **Phase 4 replaces the stub consumer with the Orchestrator** — no
  contract change.

### Packaging & deployment
- **D-11:** Ship a new shared lib **`veridoc-rave`** (the Port ABC + Rave DTOs + ODM
  parsing/serialization + the HTTP adapter), a new **`rave-integration` service**
  (webhook receiver + RQ worker, Helm-deployed), and the **mock as a separate Helm-deployed
  service** (dev/CI). Add a **kind smoke test** in CI exercising READ/WRITE/webhook
  end-to-end against the deployed mock — same walking-skeleton + CI pattern as Phase 2.

### Claude's Discretion
- Exact mock state store (in-memory vs lightweight persistence) — provided D-04 (stateful,
  per-run) holds.
- ODM-XML parse/serialize library choice (subject to `docs/validation/PACKAGE-LEGITIMACY.md`
  vetting before adoption).
- Internal module layout of `veridoc-rave`; exact DTO field sets within each typed model.
- Webhook auth detail on the receiver (shared-secret/HMAC vs Basic), as long as it is
  authenticated and audited.

</decisions>

<specifics>
## Specific Ideas

- Reuse the Phase 2 idioms verbatim where possible: `SourceAdapter` ABC + registry for the
  Port shape, `ingestion-service` (FastAPI + RQ worker + Dockerfile + Helm + kind smoke
  test) as the template for `rave-integration` and the mock service.
- "Swap mock → production must be config-only" is the guiding test for every boundary
  decision — the HTTP adapter is the single seam.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### MDRWS contract & requirements
- `docs/prd/veridoc-pid.md` §3.4 (Medidata Rave Integration) — authoritative READ / WRITE /
  WEBHOOKS contract and the Technology-Partner/production-access constraint.
- `.planning/REQUIREMENTS.md` → **RAVE-01** — full requirement (READ/WRITE/WEBHOOKS list +
  "abstraction layer isolates MDRWS contract so the mock can be swapped for production").
- `.planning/ROADMAP.md` → **Phase 3** — the 4 Success Criteria this phase is graded against.

### Locked project decisions
- `.planning/PROJECT.md` → **DEC-rave-primary-ecrf** (Rave/MDRWS is primary eCRF),
  **CON-medidata-partner** (mock now, production deferred), **DEC-regional-data-residency**,
  Security & Compliance Baseline (21 CFR Part 11 / Annex 11 / GDPR audit-trail rules).

### Patterns to mirror (closest analogs in-repo)
- `libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py` — `SourceAdapter` ABC +
  `SourceProfile` + registry idiom the Rave Port should mirror.
- `.planning/phases/02-fhir-r4-model-emr-ingestion/02-CONTEXT.md` — Phase 2 decisions on
  the adapter/registry/walking-skeleton pattern.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `libs/veridoc-ingestion/.../adapter.py` — ABC + dataclass-config + registry pattern;
  the **template for the Rave Port** (one interface, swappable concrete adapter).
- `libs/veridoc-crypto/.../kms.py` (`KMSKeyring`) — the canonical abstraction idiom the
  whole codebase follows.
- `libs/veridoc-audit` — `append_audit` same-transaction, hash-chained audit SDK (D-05).
  **Use for every query-lifecycle event and every webhook receipt** (PLAT-02).
- `libs/veridoc-pseudonym` — `pseudonym_token(...)` (D-12/D-14) for the Rave `Subject` ID.
- `services/ingestion-service` — FastAPI app + RQ worker + Dockerfile; **clone as the
  template** for `rave-integration` (webhook receiver + worker) and for the mock service.
- `deploy/` Helm charts (e.g. `ingestion-service.yaml`, `mongodb.yaml`) + the Taskfile/CI
  kind smoke-test wiring — the **deploy + CI template** for the two new services.

### Established Patterns
- **RQ + JSONSerializer** (DEC-rq-json-serializer): webhook event payloads must be
  JSON-serializable primitives; no pickle, no raw bytes.
- **Fail-closed tenancy + RS256/MFA-gated APIs** (DEC-tenancy-fail-closed,
  DEC-auth-direct-jwt): the `rave-integration` service inherits the same auth/tenancy
  posture as `ingestion-service` for any inbound API surface.
- **Audit writer never commits** (DEC-audit-same-txn-writer): audit append joins the
  caller's session.

### Integration Points
- **Phase 4 (Orchestrator):** subscribes to the **`rave-events`** RQ queue, replacing the
  Phase-3 stub consumer (D-10) — the queue + event contract is the seam.
- **Phase 5 (SDV agent):** consumes the typed Rave DTOs (D-05/D-06) and uses the
  site-level EMR↔Rave subject mapping (D-08) to correlate FHIR source vs eCRF.
- **`veridoc-audit` (Postgres):** the audit store for query-lifecycle + webhook events.

</code_context>

<deferred>
## Deferred Ideas

- Production MDRWS access + Technology-Partner integration — deferred (CON-medidata-partner;
  the config-only swap seam D-01 is the hand-off point).
- Full query-lifecycle automation (generation, priority classification, response
  evaluation, escalation thresholds) — **Phase 6 (Query Agent)**; Phase 3 only delivers the
  WRITE primitives + stateful mock that Phase 6 drives.
- Orchestrated handling of dispatched webhook events — **Phase 4** (replaces the stub
  consumer).

</deferred>

---

*Phase: 03-medidata-rave-mock-integration*
*Context gathered: 2026-06-12*
