# VeriDoc Secrets Contract — Phase 1

> **Validation evidence (GAMP 5 / DEC-gamp5-csv).** Enumerates every secret the Phase-1
> platform consumes, its origin, and how it is delivered. **Invariant (T-06-01): no secret
> value is ever committed to git** — secrets are delivered as **Kubernetes Secrets referenced
> by name**, and a CI grep gate fails the build if a plaintext credential appears in the chart.

## Trust boundary

The boundary is **CI/operator → cluster**. Secret *material* is injected at deploy time by the
operator (CI: `kubectl create secret`; prod: sealed-secrets / external-secrets / cloud KMS) and
never crosses the **git → deployed-config** boundary. The Helm chart carries only secret *names*
and *keys* (`values.yaml → secrets:`, consumed via `secretKeyRef` / `envFrom`), never values.

## Secret register

| # | Secret (K8s name) | Key | Consumed by | Origin | Delivery | Rotation |
|---|-------------------|-----|-------------|--------|----------|----------|
| 1 | `veridoc-postgres` | `POSTGRES_USER` | Postgres, reference-service | Operator-chosen app user | K8s Secret → `secretKeyRef` | On-demand; app reconnects |
| 2 | `veridoc-postgres` | `POSTGRES_PASSWORD` | Postgres, reference-service | Generated (CSPRNG) | K8s Secret → `secretKeyRef` | Rotate + roll pods |
| 3 | `veridoc-postgres` | `POSTGRES_DB` | Postgres, reference-service | Operator-chosen DB name (`veridoc`) | K8s Secret → `secretKeyRef` | Static |
| 4 | `veridoc-redis` | `REDIS_PASSWORD` | Redis, (later) session layer | Generated (CSPRNG) | K8s Secret → `secretKeyRef` (`--requirepass`) | Rotate + roll pods |
| 5 | `veridoc-keycloak` | `KEYCLOAK_ADMIN` | Keycloak | Operator-chosen bootstrap admin | K8s Secret → `KC_BOOTSTRAP_ADMIN_USERNAME` | Rotate post-bootstrap |
| 6 | `veridoc-keycloak` | `KEYCLOAK_ADMIN_PASSWORD` | Keycloak | Generated (CSPRNG) | K8s Secret → `KC_BOOTSTRAP_ADMIN_PASSWORD` | Rotate post-bootstrap |
| 7 | `veridoc-keycloak` | `REFERENCE_SERVICE_CLIENT_SECRET` | Keycloak (realm import) + reference-service | Generated (CSPRNG) | K8s Secret; resolves the realm `${REFERENCE_SERVICE_CLIENT_SECRET}` placeholder at import, and the service's `VERIDOC_CLIENT_SECRET` | Rotate in realm + service together |
| 8 | `veridoc-kms` | `VERIDOC_MASTER_KEY` | reference-service (`veridoc-crypto`) | Per-patient key hierarchy master key; in prod **wrapped by cloud KMS** (DEC-cloud-provider OPEN) | K8s Secret → `VERIDOC_MASTER_KEY` | KMS-managed; rotation re-wraps DEKs |

### Notes per secret

- **Postgres (#1–3):** the reference service assembles `VERIDOC_DATABASE_URL` from
  `VERIDOC_DB_USER`/`VERIDOC_DB_PASSWORD`/`VERIDOC_DB_NAME` (all `secretKeyRef`) at runtime —
  the URL is never stored with embedded credentials in the chart.
- **Redis (#4):** Redis is started with `--requirepass "$REDIS_PASSWORD"`; the value comes only
  from the Secret. (Session wiring lands in a later phase; the credential contract is fixed now.)
- **Keycloak admin (#5–6):** bootstrap admin creds; rotate after first boot per Annex 11 access
  control. Keycloak owns all end-user credentials/MFA (D-01) — the platform never handles them.
- **Reference-service OIDC client secret (#7):** the realm JSON (`deploy/keycloak/veridoc-realm.json`)
  stores the literal placeholder `${REFERENCE_SERVICE_CLIENT_SECRET}` (T-04-06) — Keycloak
  substitutes the env-injected value during `--import-realm`. The same value is injected into the
  reference service as `VERIDOC_CLIENT_SECRET`.
- **KMS master key (#8):** anchors the per-patient HKDF key hierarchy (`veridoc-crypto`,
  plan 01-03). In production the master key is wrapped by AWS KMS / Azure Key Vault (provider
  decided later); the Secret carries a key *reference*, and crypto-shredding erases per-patient
  derivation material (GDPR Art. 17, plan 01-03/01-05).

## CI delivery (kind, ephemeral)

In GitHub Actions the four Secrets are created with **ephemeral, throwaway** values before
`helm install` (the cluster is torn down after the run), e.g.:

```bash
kubectl create secret generic veridoc-postgres \
  --from-literal=POSTGRES_USER=veridoc \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)" \
  --from-literal=POSTGRES_DB=veridoc
# ... veridoc-redis, veridoc-keycloak, veridoc-kms likewise
```

These values exist only inside the ephemeral kind cluster for the duration of the job and are
**never** written to the repo (T-06-01).

## Enforcement

- **Grep gate (CI + acceptance):** `! grep -RniE "password:\s*[\"']?[A-Za-z0-9]{6,}"
  deploy/helm/veridoc/templates/secrets.yaml` — fails the build on any inline secret.
- **No-values templates:** `deploy/helm/veridoc/templates/secrets.yaml` emits only a *contract*
  ConfigMap (names + keys), never a Secret with data.
- **Image scan:** the reference-service Dockerfile bakes **no** secrets (T-05-02); all config
  arrives via env/Secrets at runtime.

## STRIDE linkage

Mitigates **T-06-01** (Information Disclosure — secrets in Helm values / git) from
`docs/validation/THREAT-MODEL.md`.
