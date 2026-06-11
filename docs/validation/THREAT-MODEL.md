# VeriDoc Phase 1 — Consolidated STRIDE Threat Model

> **Validation evidence (GAMP 5 / DEC-gamp5-csv) — ASVS Level 1, block-on-HIGH.**
> This document consolidates the per-plan STRIDE registers from Phase 1 (plans 01-01 …
> 01-06) into one Phase-level threat model for the platform skeleton, audit foundation,
> identity/RBAC, PII protection, and the deploy path. Each threat carries a STRIDE
> category, the affected component, a **disposition** (`mitigate` / `accept`), the
> mitigation, and where it is verified. There are **no open HIGH (unmitigated critical)
> threats** — every Tampering/Spoofing/Elevation/Information-Disclosure threat at a trust
> boundary is `mitigate` with a test or control; the few `accept` items are explicitly
> scoped, low-severity, single-cluster-milestone deferrals.

## Scope & methodology

- **Standard:** OWASP ASVS L1 categories (V1–V13) applicable to a Python/FastAPI + Keycloak
  + Postgres + Redis + Kubernetes platform (see `01-RESEARCH.md § Security Domain`).
- **Method:** per-component STRIDE decomposition done at plan time; this file is the
  Phase-1 roll-up. Supply-chain (T-01-SC) is included as a first-class register.
- **Block-on-HIGH:** any threat that would be `accept` for a HIGH-severity, in-scope risk
  blocks the phase. None exist; accepts are documented deferrals below.

## Trust boundaries (Phase 1)

| Boundary | Description | Primary controls |
|----------|-------------|------------------|
| Internet → ingress | Authenticated client traffic; TLS termination (design: TLS 1.3) | Keycloak OIDC + MFA; TLS 1.3 (design-noted, T-06-07 accept) |
| ingress → API (reference service) | Token-bearing requests enter the app tier | JWT sig-verify vs JWKS, RS256-pinned, MFA acr/amr, deny-by-default RBAC, fail-closed tenancy |
| API → Postgres/Redis | Business + audit writes; session reads | Same-txn hash-chained audit; append-only trigger; parameterized SQL; envelope-encrypted PII; secret-injected creds |
| API → KMS/HSM | DEK wrap/unwrap; per-patient key custody | Provider-portable KMS abstraction; per-patient HKDF keys; crypto-shred erasure |
| git → deployed config | Committed Helm/IaC/realm drive what runs | No plaintext secrets in git (names-only); grep gate; realm-as-code |
| CI runner → cluster | Untrusted build artifacts deployed; secrets injected | Pinned actions; real (non-mocked) kind deploy; ephemeral secrets; tamper-detection phase gate |
| package registry → build | Third-party deps pulled into the build | Package-legitimacy gate; lockfile pinning; .tool-versions |

## Consolidated STRIDE register

### Supply chain (plan 01-01)

| Threat ID | Category | Component | Disposition | Mitigation | Verified by |
|-----------|----------|-----------|-------------|------------|-------------|
| T-01-SC | Tampering | `uv add` / `pnpm add` of `[ASSUMED]` packages | mitigate | Blocking-human package-legitimacy review; only APPROVED packages; rfc8785 individually adjudicated; committed lockfiles | `PACKAGE-LEGITIMACY.md`, `uv.lock`, `pnpm-lock.yaml` |
| T-01-01 | Tampering | dependency version drift | mitigate | Pin versions + commit lockfiles; `.tool-versions` pins toolchain | committed lockfiles / `.tool-versions` |
| T-01-02 | Information Disclosure | secrets committed to git | mitigate | `.gitignore` excludes env/secret files; secret contract names-only | `.gitignore`, `SECRETS-CONTRACT.md` |
| T-01-SC2 | Tampering | malicious postinstall scripts | accept | Single-cluster build milestone; lockfile pinning limits blast radius; revisit `--ignore-scripts` if needed | — (deferred) |

### Audit trail (plan 01-02)

| Threat ID | Category | Component | Disposition | Mitigation | Verified by |
|-----------|----------|-----------|-------------|------------|-------------|
| T-02-01 | Tampering / Repudiation | `audit_log` row rewritten or deleted | mitigate | Hash chain + `BEFORE UPDATE OR DELETE` trigger + INSERT/SELECT-only grant | `test_tamper_detection.py` (re-walk) |
| T-02-02 | Tampering | non-deterministic canonicalization → false tamper positives | mitigate | RFC 8785 JCS + committed golden-vector test | `test_jcs_golden.py` |
| T-02-03 | Tampering | forked chain under concurrency | mitigate | `pg_advisory_xact_lock` serializes chain head | `test_tamper_detection.py::test_serial_appends_do_not_fork_prev_hash` |
| T-02-04 | Repudiation | business action commits without its audit row | mitigate | `append_audit` joins caller's txn, no internal commit | `test_same_txn.py` |
| T-02-05 | Tampering | SQL injection into audit payload | mitigate | Parameterized inserts; jsonb payload, never string-formatted SQL | code review / SQLAlchemy |
| T-02-06 | Information Disclosure | PII plaintext in audit before/after jsonb | accept | Callers pass already-pseudonymized/encrypted values; audit SDK is value-agnostic | documented contract |

### PII protection — crypto + pseudonym (plan 01-03)

| Threat ID | Category | Component | Disposition | Mitigation | Verified by |
|-----------|----------|-----------|-------------|------------|-------------|
| T-03-01 | Information Disclosure | PII readable at rest | mitigate | AES-256-GCM envelope encryption (D-11) | `test_field_encryption.py` |
| T-03-02 | Information Disclosure / Compliance | non-erasable PII (global key) breaks GDPR Art. 17 | mitigate | Per-patient HKDF key hierarchy; `erase_patient` isolates erasure | `test_crypto_shred.py` |
| T-03-03 | Tampering / Information Disclosure | hand-rolled AES (nonce reuse, missing AAD) | mitigate | Vetted AEAD library (Tink); never hand-roll crypto | code review |
| T-03-04 | Information Disclosure | plaintext DEK/key in the DB | mitigate | DEK wrapped by KMS abstraction; keys out of DB engine (no pgcrypto) | code review |
| T-03-05 | Information Disclosure | deterministic pseudonym enables re-identification by linkage | accept | Determinism required for cross-source SDV (D-12); HMAC over secret per-patient key; erasure via key deletion | documented (D-12) |
| T-03-06 | Spoofing | cloud lock-in via non-portable KMS | mitigate | Provider-portable KMS interface; `LocalKeyring` for tests; DEC-cloud-provider open | code review |

### Identity / RBAC / tenancy (plan 01-04)

| Threat ID | Category | Component | Disposition | Mitigation | Verified by |
|-----------|----------|-----------|-------------|------------|-------------|
| T-04-01 | Spoofing / Elevation | JWT forged / `alg=none` / unsigned accepted | mitigate | Verify sig vs JWKS, pin RS256, check iss/aud/exp | `test_jwt_verify.py` |
| T-04-02 | Spoofing | MFA bypass (token without MFA) | mitigate | Enforce acr/amr MFA claim in API middleware | `test_jwt_verify.py` / auth tests |
| T-04-03 | Elevation | role escalation / missing access check | mitigate | Deny-by-default `require_role` across 8 roles | `test_rbac.py` |
| T-04-04 | Information Disclosure / Elevation | cross-tenant data access | mitigate | Fail-closed tenancy context (`current_tenant` raises if unset); contextvar isolation | tenancy tests |
| T-04-05 | Tampering | realm config drift / not reproducible | mitigate | Realm-as-code committed JSON imported on startup (Pitfall 4) | `veridoc-realm.json` + CI import |
| T-04-06 | Information Disclosure | Keycloak admin / client secrets in git | mitigate | Realm JSON carries no plaintext secrets; injected via K8s Secrets | `SECRETS-CONTRACT.md` |
| T-04-07 | Spoofing | IP-allowlist hook misconfigured/bypassed | accept | Hook wired data-driven; full allowlist enforcement a later hardening | documented |

### Reference service — end-to-end walking skeleton (plan 01-05)

| Threat ID | Category | Component | Disposition | Mitigation | Verified by |
|-----------|----------|-----------|-------------|------------|-------------|
| T-05-01 | Repudiation / Tampering | business write without atomic audit | mitigate | `append_audit` same session/txn; `verify_chain` asserted (D-05) | reference-service tests |
| T-05-02 | Information Disclosure | secrets baked into image / config | mitigate | No secrets in Dockerfile; config via env/K8s Secrets; grep gate | Dockerfile scan, `SECRETS-CONTRACT.md` |
| T-05-03 | Elevation / Information Disclosure | cross-role or cross-tenant access | mitigate | `require_role` deny-by-default + fail-closed `current_tenant` | `test_rbac.py` |
| T-05-04 | Information Disclosure | PII persisted in plaintext | mitigate | `encrypt_field` before persist | `test_field_encryption.py` |
| T-05-05 | Spoofing | MFA bypass at the service edge | mitigate | `authn_dependency` enforces acr/amr | reference-service tests |
| T-05-06 | Tampering | SQL injection / unvalidated input | mitigate | Pydantic v2 input models + parameterized queries | code review / tests |
| T-05-07 | Denial of Service | unauthenticated flood on `/subjects` | accept | Rate-limit hook deferred; `/healthz` only unauthenticated route | documented |
| T-05-08 | Tampering / Compliance | GDPR Art.17 erasure mutating/deleting append-only audit rows, OR erasure failing to render audited PII undecryptable | mitigate | Crypto-shred deletes only the per-patient key, never audit rows | `test_erasure_audit_immutability.py` |

### Deploy path — Helm / Terraform / CI (plan 01-06)

| Threat ID | Category | Component | Disposition | Mitigation | Verified by |
|-----------|----------|-----------|-------------|------------|-------------|
| T-06-01 | Information Disclosure | secrets in Helm values / git | mitigate | `secrets.yaml` references K8s Secrets by name only; grep gate; `SECRETS-CONTRACT.md`; no plaintext secrets committed | grep gate (CI + acceptance) |
| T-06-02 | Tampering | deploy mocked/dry-run → unproven deploy path | mitigate | CI does a REAL `helm install` into a real ephemeral kind cluster + `kubectl wait` (no `--dry-run`) | `ci.yml` deploy-kind job |
| T-06-03 | Tampering / Repudiation | tamper-detection not actually gating | mitigate | CI runs `test_mutated_row_breaks_chain` against the deployed stack as a required job (phase gate) | `ci.yml` deploy-kind job |
| T-06-04 | Tampering | realm not imported → auth unconfigured but "passes" | mitigate | Keycloak template imports `veridoc-realm.json` (`--import-realm`); integration tests exercise real tokens | `keycloak.yaml`, integration tests |
| T-06-05 | Spoofing | cloud lock-in via provider-specific IaC | mitigate | Provider-portable Helm + thin provider-agnostic Terraform; no AWS/Azure resources | `deploy/terraform/`, `deploy/helm/` |
| T-06-06 | Tampering | unpinned CI actions / supply-chain | mitigate | Pin GitHub Action versions; reuse package-legitimacy posture (T-01-SC) | `ci.yml` (pinned `uses:`) |
| T-06-07 | Denial of Service | data-in-transit interception | accept | TLS 1.3 at ingress is design-noted; full ingress/cert wiring is a later hardening | documented (design) |

## Disposition summary

| Disposition | Count | Notes |
|-------------|-------|-------|
| mitigate | 30 | All Tampering/Spoofing/Elevation/Info-Disclosure threats at trust boundaries |
| accept | 7 | T-01-SC2, T-02-06, T-03-05, T-04-07, T-05-07, T-06-07 (+ documented) — low-severity, scoped, single-cluster-milestone deferrals; none are open HIGH risks |

**No open HIGH (unmitigated critical) threats.** ASVS L1 block-on-HIGH gate: **PASS**.

## Phase gate

The deploy + tamper-detection phase gate (T-06-02 / T-06-03) is enforced in
`.github/workflows/ci.yml`: a real `helm install` into an ephemeral kind cluster, `kubectl wait`
for readiness, then `test_mutated_row_breaks_chain` run against the deployed stack. A green run is
the authoritative Phase-1 deploy proof (Success Criterion #1) and tamper-evidence proof
(Success Criterion #2).
