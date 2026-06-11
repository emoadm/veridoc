---
status: partial
phase: 02-fhir-r4-model-emr-ingestion
source: [02-VERIFICATION.md]
started: 2026-06-12T00:00:00Z
updated: 2026-06-12T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. VERIDOC_SITE_MODALITIES operator config is documented
expected: The CR-04 fix routes ingestion per-site by modality, read from the
`VERIDOC_SITE_MODALITIES` JSON-map config (present in `services/ingestion-service/src/ingestion_service/config.py`
and `deploy/helm/veridoc/values.yaml`). An unregistered site returns HTTP 400 by design.
A human confirms this requirement is documented in deployment/operator onboarding
materials so production deployments populate it and are not surprised by 400s.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
