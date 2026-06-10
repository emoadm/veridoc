# Key Hierarchy & Crypto-Shredding Design — Phase 01 (PLAT-03, D-11 + D-12)

> **Status: DECIDED (2026-06-11).** This document is the GAMP 5 validation-ready
> evidence record reconciling **D-11** (app-level envelope encryption) and **D-12**
> (deterministic per-patient pseudonyms + right-to-erasure by key deletion) under a
> single **per-patient key hierarchy**. It records the Task 1 (`checkpoint:decision`)
> outcome for plan 01-03 and drives Tasks 2 and 3.
>
> Tracks RESEARCH **Open Question #1** (A3 — KMS-abstraction library), **Open Question #2**
> (A7 — per-patient key hierarchy, HIGH RISK), and **Pitfall 3** (deterministic pseudonym
> vs. crypto-shredding collision).

---

## 1. Decision (Task 1 — `checkpoint:decision`, resolved)

| Decision point | Resolution | Rationale |
|----------------|------------|-----------|
| **Envelope-encryption / KMS-abstraction library** | **Google Tink (`tink`, PyPI)** — option `tink-hkdf` | One library natively wraps AWS KMS + Azure Key Vault behind one API (DEC-cloud-provider stays open); its AEAD primitives prevent nonce/AAD mistakes (RESEARCH "Don't Hand-Roll"). **APPROVED** in `docs/validation/PACKAGE-LEGITIMACY.md` (Google-official). |
| **Key hierarchy** | **Master key + per-patient key DERIVED via HKDF** | Avoids per-patient KMS-key proliferation (cost/quota), while keeping erasure isolated to a single patient (A7). |
| **Global pseudonym/encryption key** | **EXPLICITLY REJECTED** | A single global key makes single-patient GDPR Art. 17 erasure impossible — deleting it would erase *everyone* (Pitfall 3, A7). No `patient_pseudonym_map` re-identification table is introduced (D-12). |
| **Right-to-erasure (GDPR Art. 17 / Art. 9)** | **Crypto-shredding = delete the patient's HKDF derivation material** | When patient X's derivation material is destroyed, X's per-patient key can no longer be reconstructed → X's ciphertext is undecryptable AND X's deterministic pseudonym is irrecomputable, **without** deleting any rows (preserves the 15-year append-only audit trail). Other patients are unaffected. |

**`aws-encryption-sdk` is NOT installed for this library.** Only one of
`{tink, aws-encryption-sdk}` is installed per plan 01-03; the human selected **`tink`**.
Both were APPROVED in the legitimacy gate; `tink` was chosen for cleaner single-API
AWS KMS + Azure Key Vault parity.

### Options considered (Task 1)

- **`tink-hkdf` (CHOSEN)** — Google Tink + master-key/HKDF per-patient derivation.
  Pros: one library wraps AWS KMS + Azure Key Vault; AEAD prevents nonce/AAD mistakes;
  HKDF avoids per-patient KMS-key proliferation. Cons: Tink Python ecosystem smaller than
  AWS Enc SDK (verified APPROVED + Google-official in PACKAGE-LEGITIMACY.md).
- **`awsenc-hkdf` (rejected)** — AWS Encryption SDK keyrings + HKDF. AWS-first ergonomics;
  Azure parity via raw keyring is more bespoke.

---

## 2. Key hierarchy (the reconciliation of D-11 + D-12)

```
                       ┌──────────────────────────────────────┐
                       │  KMS / HSM  (AWS KMS / Azure Key Vault │
                       │  abstracted by kms.py; LocalKeyring    │
                       │  for tests — no cloud account)         │
                       └───────────────┬──────────────────────┘
                                       │ wraps / unwraps
                                       ▼
                         ┌─────────────────────────────┐
                         │   MASTER KEY (root secret)   │
                         │   loaded from config/KMS     │
                         └──────────────┬──────────────┘
                                        │ HKDF(master, salt = patient_id, info)
                       ┌────────────────┼────────────────┐
                       ▼                ▼                ▼
              per-patient key A  per-patient key B  per-patient key C
              (derived; never    (derived)          (derived)
               persisted raw)
                  │        │
        ┌─────────┘        └──────────────┐
        ▼                                 ▼
  ENCRYPTION path (veridoc-crypto)   PSEUDONYM path (veridoc-pseudonym)
  per-field DEK → AES-256-GCM        token = HMAC-SHA256(
  encrypt PII; DEK wrapped by the      per_patient_key, natural_id)
  per-patient key via Tink AEAD;       deterministic, stable across
  pack (wrapped_dek, nonce, ct)        EMR + Rave sources (D-12)
```

**Single shared per-patient key.** Both `veridoc-crypto` (field encryption) and
`veridoc-pseudonym` (deterministic token) derive from the *same* per-patient key via
`veridoc_crypto.keys.derive_patient_key(master, patient_id)`. There is no separate
global pseudonym key and no separate global encryption key (Pitfall 3).

### Derivation

- `derive_patient_key(master, patient_id)` = **HKDF** (HMAC-SHA256 extract-and-expand)
  with the `patient_id` as the per-patient salt/info, yielding a 256-bit per-patient key.
  Different `patient_id` ⇒ cryptographically distinct keys (patient isolation).
- The per-patient key is **never persisted in plaintext**; it is re-derived on demand from
  the master key + the patient's derivation material. Erasure deletes that derivation
  material so the key can never be re-derived again.

### Envelope encryption (D-11, app-level — NOT pgcrypto)

1. `encrypt_field(patient_id, plaintext)` generates a fresh per-field **DEK**.
2. AES-256-GCM (Tink AEAD) encrypts the plaintext with the DEK (random nonce ⇒ repeated
   encryptions of the same plaintext yield distinct ciphertext).
3. The DEK is **wrapped** by the per-patient key via the KMS abstraction (`kms.wrap_dek`).
4. The stored value packs `(wrapped_dek, nonce, ciphertext)` — only ciphertext + wrapped
   DEK ever land at rest; plaintext keys never touch the DB engine (no pgcrypto, T-03-04).
5. `decrypt_field` unwraps the DEK (`kms.unwrap_dek`) and AES-256-GCM decrypts.

### Deterministic pseudonym (D-12)

- `pseudonym_token(patient_id, natural_id)` = `HMAC-SHA256(derive_patient_key(master,
  patient_id), natural_id)` hex digest. Deterministic (same inputs ⇒ same token), distinct
  across patients, and **not reversible** without the per-patient key (T-03-05 accepted:
  determinism is required for cross-source SDV matching; the token is derived from a secret
  per-patient key, so linkage requires the key).

---

## 3. Crypto-shredding erasure (GDPR Art. 17 / Art. 9, D-12)

**Erasure = `erase_patient(patient_id)` deletes the patient's HKDF derivation material.**

After erasure, for the erased patient:

- the per-patient key can no longer be re-derived;
- `decrypt_field(patient_id, prior_ciphertext)` **raises** (ciphertext undecryptable —
  the wrapped DEK can no longer be unwrapped);
- `pseudonym_token(patient_id, natural_id)` is **irrecomputable** (the key is gone).

For every **other** patient, encryption and pseudonyms are **unaffected** — their
derivation material is untouched. No audit rows are deleted (the 15-year append-only
audit trail is preserved). This is proven by `libs/veridoc-crypto/tests/test_crypto_shred.py`
(erase A ⇒ A undecryptable + token irrecomputable; B intact) and the pseudonym erasure
assertion in `libs/veridoc-pseudonym/tests/test_pseudonym_deterministic.py`.

---

## 4. Provider portability (DEC-cloud-provider OPEN)

`kms.py` exposes a provider-portable interface (`wrap_dek` / `unwrap_dek`) with:

- **`LocalKeyring`** — a local, in-process keyring used by the tests so the suite runs with
  **no cloud account** (Wave 0 / clean-clone harness stays green);
- **AWS KMS** and **Azure Key Vault** adapters (interface/stub only this phase — no live
  cloud calls; wired when DEC-cloud-provider closes).

This keeps mock → production and AWS → Azure swaps trivial (T-03-06: cloud-provider
lock-in mitigated).

---

## 5. Assumption A7 — tracked & resolved

| # | Claim | Disposition |
|---|-------|-------------|
| **A7** | Per-patient key hierarchy is the intended reconciliation of D-11 + D-12 | **RESOLVED (Task 1, plan 01-03).** Master key + per-patient **HKDF-derived** keys; a global pseudonym/encryption key is **rejected**; erasure = delete the patient's derivation material. Confirmed by the human in the Task 1 decision. |

| Threat ID | Mitigation evidenced here |
|-----------|---------------------------|
| T-03-01 | AES-256-GCM envelope encryption (ciphertext ≠ plaintext) — `test_field_encryption.py` |
| T-03-02 | Per-patient HKDF hierarchy; `erase_patient` isolates erasure — `test_crypto_shred.py` |
| T-03-03 | Vetted AEAD library (Google Tink) — never hand-roll crypto |
| T-03-04 | DEK wrapped by KMS abstraction; only wrapped DEK + ciphertext stored (no pgcrypto) |
| T-03-05 | Deterministic token = HMAC(secret per-patient key, natural_id) — not reversible without the key (accepted) |
| T-03-06 | Provider-portable KMS interface + LocalKeyring for tests |

---

## 6. Sign-off

- **Decision:** `tink-hkdf` — Google Tink + master-key/HKDF per-patient derivation.
- **Reviewer:** emoadm@gmail.com (Task 1 `checkpoint:decision`, plan 01-03).
- **Date:** 2026-06-11.
- **Consistency:** `tink` is **APPROVED** (Google-official) in
  `docs/validation/PACKAGE-LEGITIMACY.md`; `aws-encryption-sdk` is **NOT** installed for
  this library.
- **Drives:** Task 2 (`keys.py` HKDF derivation + `envelope.py` AES-256-GCM + `kms.py`) and
  Task 3 (`pseudonym.py` HMAC sharing the per-patient key).
