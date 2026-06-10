{{/*
veridoc Helm chart helpers — naming + label conventions shared across templates.
Provider-portable: no cloud-specific values referenced here.
*/}}

{{/* Chart fullname (release-qualified) — used as the base for resource names. */}}
{{- define "veridoc.fullname" -}}
{{- printf "%s" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Common labels stamped on every resource (incl. the residency `region` tag). */}}
{{- define "veridoc.labels" -}}
app.kubernetes.io/part-of: veridoc
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
veridoc.ai/region: {{ .Values.global.region | quote }}
{{- with .Values.global.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{/* Per-component selector labels (component is passed in via `dict`). */}}
{{- define "veridoc.selectorLabels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end -}}

{{/* Fully-qualified, in-cluster service name for a component (stable DNS). */}}
{{- define "veridoc.componentName" -}}
{{- printf "veridoc-%s" .component -}}
{{- end -}}
