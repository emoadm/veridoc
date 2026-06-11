# Phase 2: FHIR R4 Model & EMR Ingestion - Discussion Log

> **Audit trail only.** Not consumed by downstream agents (researcher, planner,
> executor). Decisions live in `02-CONTEXT.md`.

**Date:** 2026-06-11
**Phase:** 02-fhir-r4-model-emr-ingestion
**Mode:** discuss (interactive, default)
**Areas selected:** FHIR model & storage, Ingestion architecture, OCR + NLP extraction,
Adapter scope/depth (all four offered)

---

## Area 1 — FHIR model & storage

| Question | Options presented | Selected |
|----------|-------------------|----------|
| FHIR R4 representation | fhir.resources library / hand-rolled Pydantic / you decide | **fhir.resources library** |
| Persistence store | MongoDB document store / Postgres JSONB / you decide | **MongoDB document store** |
| Provenance modeling | FHIR Provenance + Meta.source / sidecar record / you decide | **FHIR Provenance + Meta.source** |

## Area 2 — Ingestion architecture

| Question | Options presented | Selected |
|----------|-------------------|----------|
| Packaging | Shared libs + ingestion-service / single service / you decide | **Shared libs (veridoc-fhir + veridoc-ingestion) + ingestion-service** |
| Routing | SourceProfile registry + adapter interface / pipeline chain / you decide | **SourceProfile registry + adapter interface** |
| Sync vs async | Synchronous in-process / async queue now / you decide | **Async queue now** (deviation from recommended sync; OCR latency justifies it) |

## Area 3 — OCR + NLP extraction

| Question | Options presented | Selected |
|----------|-------------------|----------|
| OCR engine selection | Portable abstraction + OSS default / cloud OCR directly / you decide | **Portable abstraction + OSS default** |
| OSS OCR engine | Tesseract / docTR-PaddleOCR / you decide | **Tesseract** |
| NLP extraction depth | DocumentReference + extraction interface / full LLM extraction now / you decide | **DocumentReference + extraction interface (rule-based now)** |
| Blob store | Yes, portable blob store / defer / you decide | **Yes — portable S3-compatible blob store (MinIO local/CI)** |

## Area 4 — Adapter scope/depth

| Question | Options presented | Selected |
|----------|-------------------|----------|
| Adapter scope | Build 4 + stub proprietary / build all 5 / you decide | **Build 4 fully, proprietary-API interface-only** |
| HL7 path | Library parser + explicit mapping / hand-rolled / you decide | **Library parser + explicit mapping** |
| Synthetic data | Synthea-generated FHIR R4 / hand-authored fixtures / you decide | **Synthea-generated FHIR R4 + hand-crafted edge cases** |

## Defaults locked at readiness gate (no separate discussion)
- Pseudonymization at ingestion reuses `veridoc-pseudonym` deterministic tokens (D-12);
  every ingest writes through `veridoc-audit` SDK.
- Semi-manual PDF/Excel path uses the same rule-based extraction interface as OCR.

## Deferred ideas captured
- LLM-based clinical-entity extraction (waits for Phase 4 LLM engine).
- Proprietary-API adapter implementation (waits for a real contract).
- Higher-accuracy / cloud OCR (swappable behind OcrEngine abstraction).
- ALCOA+ legibility scoring agent (Phase 5, ALCOA-01).

## Scope creep redirected
- None — discussion stayed within the EMR-01 / ingestion boundary.
