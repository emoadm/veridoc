# VeriDoc IaC (Terraform) — provider-portable posture

**Phase 1 status: THIN, provider-portable, deferred managed-cluster provisioning.**

This Terraform module is deliberately minimal. It captures the *IaC posture* for VeriDoc
without committing to a cloud provider, because **DEC-cloud-provider is OPEN** (AWS vs Azure
undecided — see `.planning/PROJECT.md`). The architecture must stay AWS/Azure-portable until
that decision is made (T-06-05: avoid cloud lock-in via provider-specific IaC).

## What this module does

It deploys the **same provider-portable Helm chart** (`../helm/veridoc`) into an **existing**
Kubernetes context — in this milestone, the ephemeral `kind` cluster created in CI/dev. It
declares:

- a platform `namespace`, and
- a `helm_release` of the VeriDoc chart (Postgres + Redis + Keycloak realm-import +
  reference service),

using only the **portable** `hashicorp/kubernetes` and `hashicorp/helm` providers, which
target a kube *context* — never a cloud account. No `aws_*` or `azurerm_*` resource appears
anywhere in this module.

## What it deliberately does NOT do (this milestone)

- **Provision a managed cluster** (EKS / AKS). That is gated on DEC-cloud-provider. When the
  provider is chosen, a `modules/cluster-aws` *or* `modules/cluster-azure` is added alongside
  this root module; this root module then simply targets the new context — its chart-deploy
  logic is unchanged. The authoritative Phase-1 deploy proof is the **CI kind job**
  (`.github/workflows/ci.yml`), because the build host and CI runners have no cloud account
  (RESEARCH Pitfall 6 / Environment Availability).
- **Manage secrets.** Per T-06-01, secrets are never in IaC/values/git. The chart references
  named Kubernetes Secrets; those are created out of band (CI: `kubectl create secret`; prod:
  sealed-secrets / external-secrets / cloud KMS). See `docs/validation/SECRETS-CONTRACT.md`.
- **Provision cloud networking, storage classes, or load balancers.** All deferred to the
  provider-specific module added post-decision.

## Regional residency (DEC-regional-data-residency — design-only)

The `region` variable + `values_files` input let you apply the residency overlay
(`../helm/veridoc/values-region-eu.yaml`) so workloads carry the residency tag. This proves
the architecture *supports* regional isolation as a values overlay — it does **not** perform a
multi-region rollout (deferred).

## Usage (against a kind cluster)

```bash
cd deploy/terraform
terraform init
terraform plan \
  -var 'kube_context=kind-veridoc' \
  -var 'reference_service_image=veridoc/reference-service:ci'
terraform apply -auto-approve \
  -var 'kube_context=kind-veridoc' \
  -var 'reference_service_image=veridoc/reference-service:ci'

# EU residency overlay (design-only):
terraform apply -auto-approve \
  -var 'region=eu-west' \
  -var 'values_files=["../helm/veridoc/values-region-eu.yaml"]'
```

> Note: CI (`.github/workflows/ci.yml`) drives the kind deploy directly via `helm install`
> for a tight, fast feedback loop and to prove the chart end-to-end. This Terraform module
> documents the equivalent IaC-managed path and is the seam where the managed-cluster module
> attaches once DEC-cloud-provider is decided.
