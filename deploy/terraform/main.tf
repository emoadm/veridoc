# VeriDoc IaC — thin, provider-portable root module (D-09, DEC-cloud-provider OPEN).
#
# Posture (see README.md): this milestone proves the deploy path on a LOCAL kind cluster
# via CI; the authoritative deploy proof is the GitHub Actions kind job (services lack a
# cloud account). Terraform here is deliberately THIN — it deploys the SAME provider-portable
# Helm chart (../helm/veridoc) into an existing kube context, with NO AWS/Azure resource.
# When DEC-cloud-provider is decided, a provider-specific cluster-provisioning module is
# added alongside this one (EKS or AKS), and this root module simply targets the new context.
#
# No managed-cluster, cloud-network, or provider-specific resource is declared here — keeping
# the IaC AWS/Azure-portable (T-06-05: avoid cloud lock-in via provider-specific IaC).

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }
}

# Both providers target an EXISTING kube context (kind in CI/dev). No cloud auth required —
# the context is provider-agnostic. A managed cluster swaps only the context, not this module.
provider "kubernetes" {
  config_context = var.kube_context
}

provider "helm" {
  kubernetes {
    config_context = var.kube_context
  }
}

# Platform namespace (portable; no provider-specific annotations).
resource "kubernetes_namespace" "veridoc" {
  metadata {
    name = var.namespace
    labels = {
      "app.kubernetes.io/part-of" = "veridoc"
      "veridoc.ai/region"         = var.region
    }
  }
}

# Deploy the provider-portable VeriDoc Helm chart. Secrets are NOT managed here
# (T-06-01) — the named K8s Secrets are created out of band (CI: kubectl create secret;
# prod: sealed-secrets / external-secrets / cloud KMS). This module only references them
# by name through the chart.
resource "helm_release" "veridoc" {
  name      = var.release_name
  namespace = kubernetes_namespace.veridoc.metadata[0].name
  chart     = var.chart_path

  # Residency tag (design-only overlay).
  set {
    name  = "global.region"
    value = var.region
  }

  set {
    name  = "referenceService.image.repository"
    value = split(":", var.reference_service_image)[0]
  }

  set {
    name  = "referenceService.image.tag"
    value = try(split(":", var.reference_service_image)[1], "ci")
  }

  # Extra values files (e.g. the EU residency overlay).
  values = [for f in var.values_files : file(f)]

  # The chart deploys real workloads (not a dry-run) — Success Criterion #1.
  wait    = true
  timeout = 600
}
