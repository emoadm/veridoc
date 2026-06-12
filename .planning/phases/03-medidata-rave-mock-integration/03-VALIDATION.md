---
phase: 3
slug: medidata-rave-mock-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-12
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, APPROVED) |
| **Config file** | none — workspace-wide `pyproject.toml` per lib/service |
| **Quick run command** | `uv run pytest libs/veridoc-rave/tests/ -q` |
| **Full suite command** | `uv run pytest libs/veridoc-rave/tests/ services/rave-integration/tests/ -q` |
| **Estimated runtime** | ~30 seconds (unit + TestClient integration; kind smoke test runs in CI only) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest libs/veridoc-rave/tests/ -q`
- **After every plan wave:** Run `uv run pytest libs/veridoc-rave/tests/ services/rave-integration/tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green AND kind smoke test passing
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| ODM parse | veridoc-rave | 1 | RAVE-01 (ODM) | — | ODM-XML parses into all 6 typed DTOs; malformed XML raises typed error (no crash) | unit | `uv run pytest libs/veridoc-rave/tests/test_odm.py -q` | ❌ W0 | ⬜ pending |
| Port contract | veridoc-rave | 1 | RAVE-01 SC-4 | — | RavePort ABC cannot be instantiated; adapter swap is base_url-only | unit | `uv run pytest libs/veridoc-rave/tests/test_port_contract.py -q` | ❌ W0 | ⬜ pending |
| READ ops | veridoc-rave | 2 | RAVE-01 SC-1 | — | All 6 READ operations return typed DTOs; Subject ID pseudonymized at boundary | integration | `uv run pytest libs/veridoc-rave/tests/test_adapter_read.py -q` | ❌ W0 | ⬜ pending |
| WRITE ops | veridoc-rave | 2 | RAVE-01 SC-2 | — | WRITE then read-back round-trip confirms state change on stateful mock | integration | `uv run pytest libs/veridoc-rave/tests/test_adapter_write.py -q` | ❌ W0 | ⬜ pending |
| Webhook dispatch | rave-integration | 3 | RAVE-01 SC-3 | T-webhook-auth | Valid event → `rave:webhook:dispatched` audit row + RQ job enqueued | integration | `uv run pytest services/rave-integration/tests/test_webhook.py -q` | ❌ W0 | ⬜ pending |
| Webhook auth | rave-integration | 3 | RAVE-01 (auth) | T-webhook-auth | Invalid/missing HMAC signature → 401, no audit, no enqueue (fail-closed) | unit | `uv run pytest services/rave-integration/tests/test_webhook_auth.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `libs/veridoc-rave/tests/conftest.py` — mock service fixture (`TestClient(create_mock_app())`, no testcontainer)
- [ ] `libs/veridoc-rave/tests/fixtures/subject_odm.xml` — sample ODM READ response fixture
- [ ] `libs/veridoc-rave/tests/fixtures/write_response.xml` — sample POST success response fixture
- [ ] `libs/veridoc-rave/tests/test_odm.py` — ODM parsing unit tests (all 6 DTO types)
- [ ] `libs/veridoc-rave/tests/test_port_contract.py` — ABC contract enforcement tests
- [ ] `libs/veridoc-rave/tests/test_adapter_read.py` — READ operations against mock TestClient
- [ ] `libs/veridoc-rave/tests/test_adapter_write.py` — WRITE + read-back round-trip
- [ ] `services/rave-integration/tests/conftest.py` — DB + RQ fixtures (testcontainer Postgres)
- [ ] `services/rave-integration/tests/test_webhook.py` — webhook auth + audit + enqueue
- [ ] `services/rave-integration/tests/test_webhook_auth.py` — HMAC signature rejection
- [ ] `pytest` framework — already installed (no new framework install needed)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end READ/WRITE/webhook against the *deployed* mock in a kind cluster | RAVE-01 SC-1/2/3/4 | Requires a live kind cluster + Helm-deployed services (not reproducible in a unit-test process); runs in CI | Run `task deploy:kind` then the `Rave smoke test` CI step; assert SC-1 typed read, SC-2 write+read-back, SC-3 audit row, SC-4 config-only swap |
| Production MDRWS attribute-name fidelity (freeze/lock `mdsol:Frozen`/`mdsol:Locked`, `mdsol:Verify`, prod webhook auth) | RAVE-01 (open questions A2/A3/A7) | Behind CON-medidata-partner wall — cannot verify against real Rave until partner access clears | Persist as UAT/validation item; verify when CON-medidata-partner clears. Mock implements the assumed contract; swap seam (SC-4) is the hand-off point |

*Note: the kind smoke test is automated in CI but is "manual" relative to the per-task pytest sampling loop (it cannot run inside the quick/full local suite).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
