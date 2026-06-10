# VeriDoc IaC — provider-portable input variables (DEC-cloud-provider OPEN).
#
# These variables describe the *target cluster* abstractly. No AWS/Azure-specific
# variable appears here: the same definitions hold whether the cluster is local kind,
# EKS, or AKS once DEC-cloud-provider is decided. The Terraform in this phase is THIN
# (deploys the Helm chart into an already-existing kube context); managed-cluster
# provisioning modules are added under the chosen provider when that decision lands.

variable "kube_context" {
  description = "kubectl context for the target cluster (e.g. the kind context in CI/dev)."
  type        = string
  default     = "kind-veridoc"
}

variable "namespace" {
  description = "Kubernetes namespace the VeriDoc platform is deployed into."
  type        = string
  default     = "veridoc"
}

variable "release_name" {
  description = "Helm release name for the VeriDoc chart."
  type        = string
  default     = "veridoc"
}

variable "chart_path" {
  description = "Path to the VeriDoc Helm chart (provider-portable)."
  type        = string
  default     = "../helm/veridoc"
}

variable "region" {
  description = <<-EOT
    Regional-residency tag (DEC-regional-data-residency, DESIGN-ONLY). Passed through to
    the chart's global.region so workloads carry the residency label. Does NOT trigger a
    multi-region rollout this milestone; it proves residency-as-overlay support.
  EOT
  type        = string
  default     = "us-east"
}

variable "values_files" {
  description = "Extra Helm values files (e.g. values-region-eu.yaml for the EU overlay)."
  type        = list(string)
  default     = []
}

variable "reference_service_image" {
  description = "Reference-service image reference (repo:tag) deployed by the chart."
  type        = string
  default     = "veridoc/reference-service:ci"
}
