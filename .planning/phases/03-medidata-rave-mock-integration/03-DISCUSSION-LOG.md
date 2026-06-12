# Phase 3: Medidata Rave Mock Integration - Discussion Log

> **Audit trail only.** Not consumed by downstream agents (researcher, planner,
> executor). Decisions live in `03-CONTEXT.md`; this log preserves the discussion.

**Date:** 2026-06-12
**Phase:** 03-medidata-rave-mock-integration
**Mode:** discuss (default, interactive)
**Language note:** Discussion conducted in Bulgarian at the user's request; decisions
recorded in English.
**Areas selected:** Mock & boundary, Data contract, Webhook mechanism, Packaging & deploy

---

## Area: Mock & boundary

**Q1 — Where to place the abstraction seam / what is the mock?**
- Options: Wire-level HTTP mock (Port ABC + single HTTP adapter; FastAPI mock) [recommended]
  / In-process Python fake / Explain more.
- **Selected:** Wire-level HTTP mock.
- Rationale: highest-fidelity mock→production swap (base URL only); production HTTP
  adapter is exercised in tests.

**Q2 — How faithfully should the mock emulate real MDRWS (URLs, auth, errors)?**
- Options: Faithful but scoped to used endpoints [recommended] / Pragmatic-simplified /
  You decide.
- **Selected:** Faithful but scoped to used endpoints (real RWS URLs + HTTP Basic auth +
  ODM errors), documented as the contract.

## Area: Data contract

**Q3 — What object do agents see at the Rave boundary?**
- Options: Typed Rave DTOs (ODM on wire, hidden) [recommended] / Raw ODM-XML to agents /
  Map eCRF into FHIR.
- **Selected:** Typed Rave DTOs; ODM-XML stays adapter-internal.

**Q4 — Subject identity & pseudonymization / FHIR linkage?**
- Options: Pseudonymize with same mechanism + site mapping [recommended] / Pseudonymize
  now, defer linkage to Phase 5 / Clear IDs (synthetic data).
- **Selected:** Pseudonymize Subject ID with `veridoc-pseudonym`; EMR↔Rave correlation via
  site-level mapping outside agent code.

## Area: Webhook mechanism

**Q5 — How does the webhook mechanism work?**
- Options: Real HTTP receiver + RQ [recommended] / In-process event-callback / You decide.
- **Selected:** Real HTTP receiver; mock POSTs as Rave; receiver → audit + RQ enqueue.

**Q6 — What is the "pipeline action" within Phase-3 scope (orchestrator is Phase 4)?**
- Options: Thin verifiable dispatch + stub consumer [recommended] / Endpoint + mapping
  table only / You decide.
- **Selected:** Thin verifiable dispatch — event→named action map, audit + typed RQ job on
  `rave-events` queue, stub consumer (no-op + `rave:webhook:dispatched`). Phase 4 replaces
  the stub.

## Area: Packaging & deploy

**Q7 — How to package and deploy?**
- Options: Lib + integration service + mock service (all Helm) [recommended] / Lib +
  integration service (Helm), mock = test fixture / Lib only, rest in tests.
- **Selected:** `veridoc-rave` lib + `rave-integration` service (Helm) + mock service
  (Helm, dev/CI) + kind smoke test.

## Closing decision

**Q8 — Ready for CONTEXT, or discuss more?**
- **Selected:** Ready for CONTEXT. Confirmed the **stateful mock** default (mock persists
  query/flag/PD state per run so WRITE + status-update is verifiable end-to-end —
  Success Criterion #2).

---

## Deferred ideas captured
- Production MDRWS / Technology-Partner integration (CON-medidata-partner).
- Full query-lifecycle automation → Phase 6 (Query Agent).
- Orchestrated webhook-event handling → Phase 4.

## Claude's discretion items
- Mock state store implementation; ODM library choice (pending PACKAGE-LEGITIMACY vetting);
  `veridoc-rave` internal layout & DTO field sets; webhook receiver auth detail.
