---
phase: 01-platform-skeleton-audit-foundation
plan: 03
subsystem: crypto
tags: [tink, aes-256-gcm, envelope-encryption, hkdf, per-patient-key, kms, crypto-shred, pseudonym, hmac-sha256, gdpr-art17, d-11, d-12]

# Dependency graph
requires:
  - 01-01 uv workspace members libs/veridoc-crypto + libs/veridoc-pseudonym + APPROVED package gate (tink)
provides:
  - "veridoc_crypto.derive_patient_key(master, patient_id) -> bytes (RFC 5869 HKDF, per-patient isolation)"
  - "veridoc_crypto.encrypt_field(patient_id, plaintext) -> bytes (AES-256-GCM envelope; DEK wrapped by per-patient key)"
  - "veridoc_crypto.decrypt_field(patient_id, ciphertext) -> str (round-trip; raises KeyErasedError if erased)"
  - "veridoc_crypto.erase_patient(patient_id) -> None (crypto-shred: delete derivation material, GDPR Art. 17)"
  - "veridoc_crypto.kms.KMSKeyring (wrap_dek/unwrap_dek) + LocalKeyring (no-cloud tests) + AWS KMS / Azure KV stubs"
  - "veridoc_pseudonym.pseudonym_token(patient_id, natural_id) -> str (deterministic HMAC-SHA256 over the shared per-patient key)"
  - "docs/validation/KEY-HIERARCHY.md (D-11+D-12 reconciliation evidence; A7 resolved)"
affects: [01-05-reference-service]

# Tech tracking
tech-stack:
  added: [tink 1.15.0]
  patterns:
    - "Per-patient key hierarchy: master key + RFC 5869 HKDF(master, patient_id) -> per-patient key; ONE key shared by encryption + pseudonym (Pitfall 3)"
    - "Envelope encryption: per-field DEK -> AES-256-GCM (Tink AEAD) -> DEK wrapped by per-patient key via KMS abstraction; pack (wrapped_dek, ciphertext); patient_id bound as AAD"
    - "Crypto-shred erasure = delete the patient's derivation material so the per-patient key is irrecoverable -> ciphertext undecryptable + token irrecomputable, others intact (GDPR Art. 17)"
    - "Provider-portable KMS interface (wrap_dek/unwrap_dek); LocalKeyring runs tests with no cloud account; AWS KMS / Azure Key Vault are interface stubs (DEC-cloud-provider OPEN)"
    - "Tink AEAD built deterministically from a raw 32-byte key (AesGcmKey proto, RAW prefix) so an HKDF output can act as the DEK-wrapping key without hand-rolling AES"

key-files:
  created:
    - libs/veridoc-crypto/src/veridoc_crypto/keys.py
    - libs/veridoc-crypto/src/veridoc_crypto/kms.py
    - libs/veridoc-crypto/src/veridoc_crypto/envelope.py
    - libs/veridoc-crypto/tests/test_field_encryption.py
    - libs/veridoc-crypto/tests/test_crypto_shred.py
    - libs/veridoc-pseudonym/src/veridoc_pseudonym/pseudonym.py
    - libs/veridoc-pseudonym/tests/test_pseudonym_deterministic.py
    - docs/validation/KEY-HIERARCHY.md
  modified:
    - libs/veridoc-crypto/src/veridoc_crypto/__init__.py
    - libs/veridoc-crypto/pyproject.toml
    - libs/veridoc-pseudonym/src/veridoc_pseudonym/__init__.py
    - libs/veridoc-pseudonym/pyproject.toml
    - uv.lock

key-decisions:
  - "tink-hkdf (Task 1 checkpoint:decision, resolved by human): Google Tink backs the KMS abstraction; aws-encryption-sdk NOT installed for this lib (only one of the two is used). tink APPROVED + Google-official in PACKAGE-LEGITIMACY.md"
  - "Master key + per-patient HKDF-derived key hierarchy; a global pseudonym/encryption key is EXPLICITLY REJECTED (Pitfall 3, A7) — a global key makes single-patient GDPR erasure impossible"
  - "Erasure = delete the patient's HKDF derivation material (crypto-shred); preserves the 15-year append-only audit trail (no row deletes)"
  - "HKDF is RFC 5869 over the Python stdlib (hmac/hashlib) — a standard KDF, not hand-rolled AEAD; the field/DEK AEAD uses the vetted Tink library"
  - "patient_id is bound as AAD on both the field ciphertext and the wrapped DEK, so a ciphertext encrypted under patient A cannot be decrypted under patient B"

requirements-completed: [PLAT-03]

# Metrics
duration: ~30min
completed: 2026-06-11
---

# Phase 01 Plan 03: veridoc-crypto + veridoc-pseudonym (Per-Patient Key Hierarchy) Summary

**Two shared platform libs built TOGETHER under ONE per-patient key hierarchy: `veridoc-crypto` does app-level AES-256-GCM envelope encryption (Google Tink) behind a provider-portable KMS abstraction, `veridoc-pseudonym` derives deterministic HMAC-SHA256 patient tokens from the SAME master-key + HKDF per-patient key, and GDPR right-to-erasure is crypto-shredding — deleting one patient's derivation material makes their ciphertext undecryptable AND their pseudonym irrecomputable while every other patient is untouched.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-06-11
- **Tasks:** 3 (Task 1 = pre-resolved checkpoint:decision recorded; Tasks 2 & 3 = TDD RED→GREEN)
- **Files:** 8 created, 5 modified
- **Tests:** 16 (10 crypto + 6 pseudonym), all green with no cloud account / no DB / no Docker.

## Accomplishments

- **Task 1 decision recorded (no pause):** `docs/validation/KEY-HIERARCHY.md` records the human's `tink-hkdf` choice — Google Tink backs the KMS abstraction, master-key + per-patient HKDF derivation, a global key is **explicitly rejected** (Pitfall 3, A7), erasure = delete derivation material. `tink` is APPROVED (Google-official) in PACKAGE-LEGITIMACY.md; `aws-encryption-sdk` is NOT installed for this lib.
- **Per-patient key hierarchy (D-11+D-12, A7):** `keys.derive_patient_key(master, patient_id)` = RFC 5869 HKDF(HMAC-SHA256) → distinct 256-bit per-patient keys. One key serves both encryption and pseudonym (no separate/global key).
- **Envelope field encryption (D-11, not pgcrypto):** `encrypt_field` generates a per-field DEK, AES-256-GCM (Tink AEAD) encrypts the PII, wraps the DEK with the per-patient key via the KMS abstraction, and packs `(wrapped_dek, ciphertext)`; `decrypt_field` reverses it. Ciphertext ≠ plaintext, round-trips, and repeated encryptions are distinct (fresh DEK + random nonce). `patient_id` is bound as AAD so cross-patient decrypt fails.
- **Provider-portable KMS (T-03-06, DEC-cloud-provider OPEN):** `kms.KMSKeyring` (`wrap_dek`/`unwrap_dek`) with a `LocalKeyring` test impl (no cloud account) plus `AwsKmsKeyring` + `AzureKeyVaultKeyring` interface stubs.
- **Crypto-shred erasure (D-12, GDPR Art. 17):** `erase_patient(A)` deletes A's derivation material → `decrypt_field(A, prior_ct)` raises `KeyErasedError` AND `pseudonym_token(A, …)` is irrecomputable, while B's encryption + token are untouched. No audit rows are deleted (15-yr append-only trail preserved).
- **Deterministic pseudonym (D-12):** `pseudonym_token(patient_id, natural_id)` = `HMAC-SHA256(derive_patient_key(master, patient_id), natural_id)` hex digest — deterministic across calls, distinct across patients and natural_ids, irreversible without the key, and sharing the crypto key hierarchy (imports `get_patient_key` from `veridoc_crypto`).

## Task Commits

1. **Task 1 — KMS-library + key-design decision (recorded):** `64d384e` `docs(01-03)` — KEY-HIERARCHY.md (tink-hkdf, per-patient HKDF, reject global key, erasure = delete derivation material).
2. **Task 2 — per-patient key hierarchy + envelope field encryption (RED→GREEN):**
   - RED `cbf8796` `test(01-03)` — failing field-encryption + crypto-shred tests.
   - GREEN `6351b1e` `feat(01-03)` — `keys.py` (HKDF + erase), `kms.py` (Tink AEAD wrap/unwrap + LocalKeyring + AWS/Azure stubs), `envelope.py` (AES-256-GCM envelope), exports; `tink` installed.
3. **Task 3 — deterministic pseudonym token (RED→GREEN):**
   - RED `7f5708a` `test(01-03)` — failing determinism + erasure tests; `veridoc-crypto` wired as a `veridoc-pseudonym` dependency.
   - GREEN `0697ce1` `feat(01-03)` — `pseudonym.py` (HMAC over the shared per-patient key) + export.

**Plan metadata:** committed separately with this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md updates.

## Verification

- `uv run pytest libs/veridoc-crypto/tests/test_field_encryption.py libs/veridoc-crypto/tests/test_crypto_shred.py -x -q` → **10 passed** (Task 2 acceptance).
- `uv run pytest libs/veridoc-pseudonym/tests/test_pseudonym_deterministic.py -x -q` → **6 passed** (Task 3 acceptance).
- `uv run pytest libs/veridoc-crypto/tests/ libs/veridoc-pseudonym/tests/ -x -q` → **16 passed** (plan verification).
- Full lib suite (`uv run pytest libs/ -q`) → crypto+pseudonym green, audit unchanged (its 7 DB tests skip cleanly with no Docker/DB — plan 01-02 pattern).
- `uv run ruff check .` and `uv run ruff format --check .` → clean across the whole repo.
- `tink 1.15.0` installed; `aws-encryption-sdk` **NOT** installed (verified via `uv pip list`).

## Decisions Made

- **tink-hkdf** (human Task 1 decision): Google Tink for the KMS abstraction; aws-encryption-sdk excluded for this lib. Both were APPROVED; Tink chosen for cleaner single-API AWS KMS + Azure Key Vault parity.
- **Master + per-patient HKDF** hierarchy; **global key rejected** (Pitfall 3, A7); **erasure = delete derivation material** (crypto-shred).
- **HKDF via stdlib (RFC 5869)** for key derivation (standard KDF, not hand-rolled AEAD); **Tink AEAD** for all AES-256-GCM (field encryption + DEK wrapping).
- **AAD = patient_id** binds ciphertext and wrapped DEK to the patient (cross-patient decrypt fails closed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical correctness] Cross-patient decrypt isolation via AAD binding**
- **Found during:** Task 2 (envelope design).
- **Issue:** The plan requires per-patient isolation but did not specify binding the ciphertext to the patient. Without it, a DEK/ciphertext could in principle be replayed under a different patient context, weakening the per-patient guarantee (T-03-02/T-03-04).
- **Fix:** Bound `patient_id` as AEAD associated data (AAD) on both the field ciphertext and the wrapped DEK. Added `test_cross_patient_decrypt_fails` asserting a `TinkError` when decrypting A's ciphertext under B.
- **Files modified:** `libs/veridoc-crypto/src/veridoc_crypto/envelope.py`, `libs/veridoc-crypto/tests/test_field_encryption.py`.
- **Commit:** `6351b1e` (test in `cbf8796`).

**2. [Rule 3 - Blocking] HKDF without the `cryptography` package**
- **Found during:** Task 2 (`keys.py`).
- **Issue:** The `cryptography` package (which exposes `HKDF`) is not installed and is not in the APPROVED gate; installing a new package is explicitly excluded from auto-fix.
- **Fix:** Implemented RFC 5869 HKDF (extract-and-expand) over the Python **stdlib** `hmac`/`hashlib` — a standard, well-specified KDF, not hand-rolled AEAD. No new package installed. The catastrophic-to-DIY part (AEAD/key-wrapping) still goes through the vetted Tink library.
- **Files modified:** `libs/veridoc-crypto/src/veridoc_crypto/keys.py`.
- **Commit:** `6351b1e`.

**3. [Rule 3 - Blocking] Docker absent — tests must run without containers**
- **Found during:** Tasks 2 & 3.
- **Issue:** Docker is not available on this host (RESEARCH Pitfall 6); the environment note directs following the plan 01-02 resolve→skip pattern for any container/DB need.
- **Fix:** Both libs are **pure in-process** (Tink AEAD + stdlib HKDF + an in-memory `LocalKeyring`/keystore) — no Postgres, Redis, or Docker is required. All 16 tests run on a clean clone with no cloud account, matching the Wave 0 harness contract. (No `VERIDOC_TEST_DATABASE_URL` / testcontainers path is needed for this plan.)
- **Files:** n/a (design choice — `LocalKeyring` is the no-cloud KMS impl).
- **Commit:** n/a (inherent to the implementation).

**Total deviations:** 3 (1 critical-correctness, 2 blocking-environment). No architectural changes; no scope creep; the only install (`tink`) is APPROVED, and `aws-encryption-sdk` was correctly NOT installed.

## Issues Encountered

- Ruff flagged `B017` (blind `pytest.raises(Exception)`) on the cross-patient test — tightened to `tink.TinkError`. `I001` import-sort auto-fixed by `ruff --fix` + `ruff format`. Resolved within the task.

## Known Stubs

`AwsKmsKeyring` and `AzureKeyVaultKeyring` raise `NotImplementedError` — these are **intentional portability interface stubs** this phase (DEC-cloud-provider is OPEN; no live cloud calls until it closes), exactly as the plan's `<action>` specifies ("interface only — no live cloud calls this phase"). `LocalKeyring` is the fully-working no-cloud implementation the tests and reference service use. These stubs do not block the plan goal (field encryption + pseudonym + crypto-shred all work end-to-end via `LocalKeyring`); the cloud adapters wire in when DEC-cloud-provider resolves.

## TDD Gate Compliance

Both implementation tasks followed RED→GREEN: each `test(01-03)` commit precedes its `feat(01-03)` commit in git history (`cbf8796`→`6351b1e`, `7f5708a`→`0697ce1`). No REFACTOR commits were needed (implementations were clean on first green; lint/format applied within the GREEN step). Task 1 is a documentation decision (`docs(01-03)`), not a behavior-adding task.

## Next Plan Readiness

- `veridoc_crypto` exports `encrypt_field`, `decrypt_field`, `erase_patient`, `derive_patient_key`, `get_patient_key`, `patient_key_exists`, `KeyErasedError`, and the KMS keyrings; `veridoc_pseudonym` exports `pseudonym_token`. Plan 01-05 (reference service) consumes both to encrypt PII + emit deterministic tokens before the same-transaction audit write (the audit SDK is value-agnostic per 01-02's caller contract — it receives already-encrypted/pseudonymized values).
- When DEC-cloud-provider closes, wire Tink's AWS KMS / Azure Key Vault integration into `AwsKmsKeyring` / `AzureKeyVaultKeyring` (the interface is already in place) and source the master key from the chosen KMS.
- `docs/validation/KEY-HIERARCHY.md` is the GAMP 5 validation-ready evidence for the D-11+D-12 reconciliation (A7 resolved).

## Self-Check: PASSED

All 9 declared key-files (8 created + this SUMMARY) verified present on disk; all five task commits (`64d384e`, `cbf8796`, `6351b1e`, `7f5708a`, `0697ce1`) verified in git history. `uv run pytest libs/veridoc-crypto/tests/ libs/veridoc-pseudonym/tests/ -x -q` exits 0 (16 passed) with no cloud account / no DB / no Docker; `uv run ruff check .` + `ruff format --check .` clean repo-wide. `tink` installed (APPROVED); `aws-encryption-sdk` NOT installed.

---
*Phase: 01-platform-skeleton-audit-foundation*
*Completed: 2026-06-11*
