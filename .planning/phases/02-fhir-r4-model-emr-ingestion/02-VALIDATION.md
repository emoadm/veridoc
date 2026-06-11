---
phase: 2
slug: fhir-r4-model-emr-ingestion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` § Validation Architecture. Per-task rows are
> finalized by the planner against the generated PLAN.md files.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (`--import-mode=importlib`, `testpaths = ["libs","services"]` per Phase 1) |
| **Config file** | root `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest libs/veridoc-fhir libs/veridoc-ingestion -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~TBD (planner to confirm; OCR/queue integration tests dominate) |

---

## Sampling Rate

- **After every task commit:** Run quick run command for the touched package
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** TBD (planner to set; keep < 120s for the quick path)

---

## Per-Task Verification Map

> Populated by the planner once PLAN.md waves exist. One row per task, each
> mapped to a phase success criterion / EMR-01 sub-requirement.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (planner fills) | | | EMR-01 | | | | | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

> The four phase success criteria need fixtures + test scaffolds before
> implementation. Planner finalizes; candidates from RESEARCH.md:

- [ ] Synthea-generated FHIR R4 bundle fixtures + hand-crafted `AdverseEvent` edge case (native-path / SC-1)
- [ ] HL7 v2.x sample messages (ADT_A01, ORU_R01) + structured PDF/Excel fixtures (SC-2)
- [ ] Scanned/paper document fixture(s) with known legibility for OCR-confidence assertions (SC-3)
- [ ] `tests/conftest.py` shared fixtures: Mongo (test db), MinIO/blob, Redis queue (eager/sync mode for tests)
- [ ] PII-bearing fixture to assert ingestion-time pseudonymization via `veridoc-pseudonym` (SC-4)

*Wave 0 covers all four success criteria as test stubs before adapters are built.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| (planner fills, or "All phase behaviors have automated verification.") | EMR-01 | | |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
