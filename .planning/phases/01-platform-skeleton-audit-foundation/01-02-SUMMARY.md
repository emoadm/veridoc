---
phase: 01-platform-skeleton-audit-foundation
plan: 02
subsystem: audit
tags: [rfc8785, jcs, sha256, hash-chain, sqlalchemy, alembic, psycopg, pydantic, postgres, advisory-lock, tamper-evident, 21cfr-part11]

# Dependency graph
requires:
  - 01-01 uv workspace member libs/veridoc-audit (import veridoc_audit) + APPROVED package gate
provides:
  - "veridoc_audit.canonicalize(payload) -> bytes (RFC 8785 JCS, deterministic)"
  - "veridoc_audit.compute_record_hash(prev_hash, payload) -> str (SHA-256(prev || JCS(payload)))"
  - "veridoc_audit.verify_chain(rows | Session) -> bool (re-walk; False if broken/tampered)"
  - "veridoc_audit.append_audit(session, AuditEvent) -> record_hash (same-txn, advisory-locked, no commit)"
  - "veridoc_audit.AuditEvent (D-06 fields incl. nullable agent_decision/agent_confidence) + AuditLog mapped class"
  - "migrations/0001_audit_log.py — append-only audit_log table + BEFORE UPDATE OR DELETE immutability trigger"
affects: [01-05-reference-service]

# Tech tracking
tech-stack:
  added: [rfc8785 0.1.4, sqlalchemy 2.0.50, "psycopg[binary] 3.3.4", alembic 1.18.4, pydantic 2.13.4, testcontainers 4.14.2]
  patterns:
    - "Deterministic hash payload via a single _payload.build_hash_payload helper (write-side AuditEvent + read-side row reconstruction can never drift)"
    - "Same-transaction audit writer: append_audit joins the caller's Session, flushes, never commits (D-05)"
    - "pg_advisory_xact_lock serializes the chain-head read-modify-write to prevent forks (Pitfall 1)"
    - "Append-only enforced in DB by a BEFORE UPDATE OR DELETE trigger (belt-and-suspenders + least-privilege grant comment)"
    - "DB-test resolution: VERIDOC_TEST_DATABASE_URL -> testcontainers -> skip (clean-clone harness stays green)"

key-files:
  created:
    - libs/veridoc-audit/src/veridoc_audit/jcs.py
    - libs/veridoc-audit/src/veridoc_audit/chain.py
    - libs/veridoc-audit/src/veridoc_audit/_payload.py
    - libs/veridoc-audit/src/veridoc_audit/models.py
    - libs/veridoc-audit/src/veridoc_audit/sdk.py
    - libs/veridoc-audit/migrations/__init__.py
    - libs/veridoc-audit/migrations/0001_audit_log.py
    - libs/veridoc-audit/tests/test_jcs_golden.py
    - libs/veridoc-audit/tests/test_chain.py
    - libs/veridoc-audit/tests/test_tamper_detection.py
    - libs/veridoc-audit/tests/test_same_txn.py
    - libs/veridoc-audit/tests/conftest.py
  modified:
    - libs/veridoc-audit/src/veridoc_audit/__init__.py
    - libs/veridoc-audit/pyproject.toml
    - pyproject.toml
    - uv.lock
    - Taskfile.yml
  deleted:
    - libs/veridoc-audit/tests/test_smoke.py

key-decisions:
  - "Used the rfc8785 package (Trail of Bits, APPROVED authentic) for JCS — no in-house fallback (per 01-01 adjudication / RESEARCH Open Question #4)"
  - "Hash payload excludes server-assigned columns (id, created_at) and normalizes occurred_at to UTC microsecond ISO so a persisted row re-hashes to its stored record_hash"
  - "verify_chain is overloaded: a SQLAlchemy Session walks persisted rows; any other iterable walks in memory (single public name)"
  - "Advisory lock key is a fixed 64-bit constant identifying the single audit-chain stream (single-cluster milestone, per Pitfall 1 / A8)"
  - "audit_log immutability enforced by a plpgsql BEFORE UPDATE OR DELETE trigger raising check_violation; table comment documents the INSERT/SELECT-only least-privilege grant"

requirements-completed: [PLAT-02]

# Metrics
duration: ~40min
completed: 2026-06-11
---

# Phase 01 Plan 02: veridoc-audit Tamper-Evident Audit SDK Summary

**The shared audit SDK: RFC 8785 JCS canonicalization + a per-record `SHA-256(prev_hash || JCS(payload))` hash chain, an append-only Postgres `audit_log` (immutability trigger + nullable D-06 agent fields), and a same-transaction, advisory-locked `append_audit` writer — with the tamper-detection phase gate green.**

## Performance

- **Duration:** ~40 min (2 tasks, each RED -> GREEN)
- **Completed:** 2026-06-11
- **Tasks:** 2 (both TDD)
- **Files:** 12 created, 5 modified, 1 deleted (the Wave 0 smoke placeholder)
- **Tests:** 18 (11 pure unit + 7 DB-backed integration); all green against local Postgres 16, unit subset green with no DB present.

## Accomplishments

- **JCS canonicalization (D-04):** `jcs.canonicalize` delegates to `rfc8785` (Trail of Bits, APPROVED authentic). A committed golden vector (`{"b":1,"a":2,"u":"é"}` → `{"a":2,"b":1,"u":"é"}` bytes → genesis hash `85c1ca33…0911e4`) guards against serialization drift (Pitfall 2).
- **Hash chain (D-04):** `compute_record_hash(prev, payload) = SHA-256(prev.encode() + JCS(payload))`, genesis `prev_hash = ""`. `verify_chain` re-walks rows fail-closed (broken link OR tampered payload → False).
- **Append-only schema (D-06):** `migrations/0001_audit_log.py` creates `audit_log` with every D-06 column **including nullable `agent_decision` (jsonb) + `agent_confidence` (numeric)** so the immutable table never needs a Phase-4 migration; a `BEFORE UPDATE OR DELETE` trigger raises on any mutation; a table comment documents the INSERT/SELECT-only least-privilege grant.
- **Same-transaction writer (D-05):** `append_audit(session, event)` takes `pg_advisory_xact_lock` (serializes the chain head — Pitfall 1), reads `prev_hash`, computes `record_hash`, inserts the row, and **flushes without committing** — the caller's transaction owns the commit.
- **The phase gate (Success Criterion #2):** `test_mutated_row_breaks_chain` writes a 2-row chain, proves `verify_chain` True, mutates a prior row's `after` jsonb (trigger bypassed in-test to simulate a privileged tamper), and proves `verify_chain` flips to **False**.
- **Atomicity proof (Pitfall 5):** `test_same_txn` forces the audit INSERT to fail (record_hash UNIQUE collision) inside the caller's transaction and asserts the business write rolls back (zero business rows persist).

## Task Commits

1. **Task 1 — JCS + hash chain (RED→GREEN):**
   - RED `fb3bc1a` — failing golden-vector + chain unit tests (replaces Wave 0 `test_smoke.py`).
   - GREEN `c4287be` — `jcs.canonicalize`, `chain.compute_record_hash`/`verify_chain`, exports; rfc8785/sqlalchemy/psycopg/alembic/pydantic deps added.
2. **Task 2 — schema + same-txn advisory-locked writer (RED→GREEN):**
   - RED `2254a11` — tamper-detection + same-txn integration tests + ephemeral-Postgres `conftest.py`.
   - GREEN `d7ef7af` — `models.py` (AuditEvent/AuditLog), `_payload.py`, `sdk.append_audit`/`verify_chain`, `migrations/0001_audit_log.py`, `__init__` dispatch, Taskfile `test:integration`.

**Plan metadata:** committed separately with this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md updates.

## Verification

- `uv run pytest libs/veridoc-audit/tests/ -x -q` → **18 passed** (against local Postgres via `VERIDOC_TEST_DATABASE_URL`).
- Plan acceptance command `… test_tamper_detection.py::test_mutated_row_breaks_chain test_same_txn.py -x -q` → **passed**.
- Without a DB/Docker, the 11 pure unit tests pass and the 7 DB tests **skip cleanly** — the clean-clone Wave 0 harness stays green.
- `uv run ruff check .` and `uv run ruff format --check .` → clean across the whole repo.
- Direct `UPDATE`/`DELETE audit_log` raises (`test_update_blocked_by_immutability_trigger`, `test_delete_blocked_by_immutability_trigger`).
- Two serialized appends never share a `prev_hash` (`test_serial_appends_do_not_fork_prev_hash`).

## Decisions Made

- **rfc8785 (no in-house JCS):** the package is APPROVED-authentic (Trail of Bits) per 01-01, so `jcs.py` imports it; the golden-vector test is the drift guard.
- **Deterministic payload via one helper:** `_payload.build_hash_payload` is the single source of truth used by both `AuditEvent.hash_payload` (write) and `sdk._row_hash_payload` (read), normalizing `occurred_at` to a UTC microsecond ISO string and `agent_confidence` Decimal→float, so a row round-trips through Postgres and re-hashes identically.
- **Overloaded `verify_chain`:** one public name dispatches on whether the argument is a `Session` (DB walk) or an iterable of row mappings (in-memory walk).
- **Migration is dual-use:** an Alembic revision (`upgrade`/`downgrade`) AND directly callable (`apply`/`revert`) so the test fixture applies the DDL without a full Alembic env (a real env arrives with the reference service / CI).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] DB-backed tests needed a Postgres; Docker absent on the build host**
- **Found during:** Task 2 (tamper-detection / same-txn integration tests).
- **Issue:** The plan specifies "testcontainers per VALIDATION Wave 0, or a compose-managed test DB". Docker is **not** available on this host (RESEARCH Pitfall 6), so testcontainers could not start a container — the phase-gate tests could not run.
- **Fix:** Made `conftest.py` resolve a Postgres URL in order: `VERIDOC_TEST_DATABASE_URL` env var → testcontainers (when Docker exists) → skip. A local Postgres 16 cluster was already running on `127.0.0.1:5432`; a dedicated least-privilege test role + database (`veridoc_test` / `veridoc_audit_test`) were provisioned via the postgres superuser (peer auth on the local socket) and the tests run against it. No package substitution — testcontainers remains the Docker-available path and is the documented CI default.
- **Verification:** all 7 DB tests pass against the local DB; they skip cleanly when the env var/Docker are absent (clean-clone harness unaffected).
- **Committed in:** `2254a11` (conftest) / `d7ef7af` (Taskfile `test:integration` documents the env var).

**2. [Rule 2 - Critical correctness] occurred_at / agent_confidence round-trip normalization**
- **Found during:** Task 2 (verify_chain over persisted rows).
- **Issue:** A persisted row must re-hash to its stored `record_hash`. A tz-aware/naive `occurred_at` and a `numeric` `agent_confidence` do not round-trip byte-identically through Postgres (offset representation, Decimal vs float), which would cause **false tamper positives** — exactly the failure Pitfall 2 warns about.
- **Fix:** Introduced `_payload.py` normalizing `occurred_at` to a UTC microsecond ISO string and `agent_confidence` to float, used identically on the write and read sides.
- **Verification:** `test_intact_chain_verifies_true` (2-row written chain → True) plus the tamper test (mutation → False) confirm the round-trip is exact.
- **Committed in:** `d7ef7af`.

**Total deviations:** 2 auto-fixed (1 blocking-environment, 1 critical-correctness). No architectural changes; no scope creep; all installs within the APPROVED legitimacy table.

## Issues Encountered

- Ruff flagged `B017` (blind `pytest.raises(Exception)`) on the trigger tests — tightened to `sqlalchemy.exc.DBAPIError`. UP017/I001 auto-fixed by `ruff --fix` + `ruff format`. Resolved within the task.

## Known Stubs

None. The SDK is fully implemented and exercised end-to-end (canonicalize → hash → persist → verify → tamper-detect → rollback). The Alembic `env.py` migration runner is intentionally deferred to the reference-service / CI plan (the migration is directly callable via `apply()`/`revert()` and is fully tested); this is a wiring detail, not a stub in the SDK's behavior.

## Next Plan Readiness

- `veridoc_audit` exports the full public API (`canonicalize`, `compute_record_hash`, `verify_chain`, `append_audit`, `AuditEvent`, `AuditLog`) for plan 01-05 (reference service) to write through inside its request transaction.
- Plan 01-05 / 01-06 should add an Alembic `env.py` to run `0001_audit_log` as part of service migrations and set `VERIDOC_TEST_DATABASE_URL` (or provide a Docker Postgres) in CI so the DB-backed tests execute in the pipeline.
- **Contract for callers (threat T-02-06):** `before`/`after`/`agent_decision` must carry already-pseudonymized/encrypted values — the audit SDK is value-agnostic (plan 03 crypto/pseudonym helpers produce those values).

## TDD Gate Compliance

Both tasks followed RED→GREEN: `test(01-02)` commit precedes its `feat(01-02)` commit in git history (`fb3bc1a`→`c4287be`, `2254a11`→`d7ef7af`). No REFACTOR commits were needed (implementations were clean on first green; lint/format applied within the GREEN step).

## Self-Check: PASSED

All 12 declared key-files verified present on disk; all four task commits (`fb3bc1a`, `c4287be`, `2254a11`, `d7ef7af`) verified in git history. `uv run pytest libs/veridoc-audit/tests/` exits 0 (18 passed against local Postgres); pure unit subset passes with no DB present.

---
*Phase: 01-platform-skeleton-audit-foundation*
*Completed: 2026-06-11*
