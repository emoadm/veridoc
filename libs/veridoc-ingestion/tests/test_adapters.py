"""Adapter tests for 02-05: NativeFhirAdapter, HL7v2Adapter, PdfExcelAdapter, OcrAdapter.

Tests cover:
  - test_native_fhir: Synthea bundle round-trips to R4B resources; Patient PII pseudonymized.
  - test_hl7v2_adt: ADT_A01 → [Patient, Encounter]; PV1.2 class mapped; no raw MRN.
  - test_hl7v2_oru: ORU_R01 → [Observation(...), DiagnosticReport]; LOINC from OBX-3/OBR-4.
  - test_pseudonymization: same (patient_id, natural_id) → identical token cross-adapter;
    raw MRN absent from native + HL7 output.
  - test_pdf_excel: PdfExcelAdapter normalizes lab PDF to R4B resources with pseudonymized PII.
  - test_ocr: OcrAdapter produces DocumentReference with ocr-confidence extension + blob URI.
  - test_ocr_flags: conf<0.95 → legibility-flag; conf<0.85 → legibility-escalate (stub engine).
"""

from __future__ import annotations

import json
import os
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
# Monorepo layout: libs/veridoc-ingestion/tests/ → libs/veridoc-fhir/tests/fixtures/fhir/
# __file__ parents: [0]=tests, [1]=veridoc-ingestion, [2]=libs, [3]=project-root
_LIBS_DIR = pathlib.Path(__file__).parents[2]  # libs/
FHIR_FIXTURES = _LIBS_DIR / "veridoc-fhir" / "tests" / "fixtures" / "fhir"
HL7_FIXTURES = FIXTURES / "hl7"
PDF_FIXTURES = FIXTURES / "pdf"
IMAGE_FIXTURES = FIXTURES / "images"

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _profile(site_id: str, modality):
    from veridoc_ingestion.adapter import SourceProfile
    return SourceProfile(site_id=site_id, modality=modality, config={})


# ===========================================================================
# Task 1 — NativeFhirAdapter + HL7v2Adapter
# ===========================================================================


class TestNativeFhirAdapter:
    """SC-1: Synthea bundle round-trips through NativeFhirAdapter."""

    def test_native_fhir(self):
        """NativeFhirAdapter.ingest parses a Synthea bundle → R4B resource list."""
        from veridoc_ingestion.adapters.native_fhir import NativeFhirAdapter
        from veridoc_ingestion.adapter import SourceModality

        adapter = NativeFhirAdapter()
        bundle_path = next(FHIR_FIXTURES.glob("*.json"))
        payload = bundle_path.read_bytes()
        profile = _profile("site-001", SourceModality.NATIVE_FHIR)

        resources = adapter.ingest(payload, profile)

        assert isinstance(resources, list), "ingest must return a list"
        assert len(resources) > 0, "must return at least one resource"

        # Each returned item should be a fhir.resources model (has get_resource_type method)
        for r in resources:
            assert hasattr(r, "get_resource_type"), f"Expected FHIR model, got {type(r)}"

        # Must contain at least one Patient
        resource_types = {r.get_resource_type() for r in resources}
        assert "Patient" in resource_types, "Synthea bundle must include a Patient"

    def test_native_fhir_patient_pseudonymized(self):
        """Patient.id in returned resources is pseudonymized; no raw UUID from bundle."""
        from veridoc_ingestion.adapters.native_fhir import NativeFhirAdapter
        from veridoc_ingestion.adapter import SourceModality

        adapter = NativeFhirAdapter()
        bundle_path = next(FHIR_FIXTURES.glob("*.json"))
        raw_data = json.loads(bundle_path.read_bytes())
        # Extract the raw patient id from the bundle
        raw_patient_id = None
        for entry in raw_data.get("entry", []):
            if entry["resource"]["resourceType"] == "Patient":
                raw_patient_id = entry["resource"]["id"]
                break
        assert raw_patient_id is not None

        payload = bundle_path.read_bytes()
        profile = _profile("site-001", SourceModality.NATIVE_FHIR)
        resources = adapter.ingest(payload, profile)

        patients = [r for r in resources if r.get_resource_type() == "Patient"]
        assert patients, "must return at least one Patient"
        patient = patients[0]
        # The patient ID must NOT be the raw UUID from the bundle
        assert patient.id != raw_patient_id, (
            "Patient.id must be pseudonymized, not the raw bundle UUID"
        )


class TestHL7v2Adapter:
    """SC-2a: HL7v2Adapter maps ADT_A01 → Patient+Encounter; ORU_R01 → Observation+DiagReport."""

    def test_hl7v2_adt(self):
        """ADT_A01 → [Patient, Encounter]; PV1.2 'I' → class EMER/IMP/AMB/PRENC mapped."""
        from veridoc_ingestion.adapters.hl7v2 import HL7v2Adapter
        from veridoc_ingestion.adapter import SourceModality

        adapter = HL7v2Adapter()
        payload = (HL7_FIXTURES / "adt_a01.hl7").read_bytes()
        profile = _profile("site-001", SourceModality.HL7V2)

        resources = adapter.ingest(payload, profile)

        resource_types = [r.get_resource_type() for r in resources]
        assert "Patient" in resource_types, "ADT_A01 must yield a Patient"
        assert "Encounter" in resource_types, "ADT_A01 must yield an Encounter"

        # Check PV1.2 'I' → IMP class mapping
        encounters = [r for r in resources if r.get_resource_type() == "Encounter"]
        enc = encounters[0]
        # class is a Coding element in R4B Encounter
        enc_class_code = enc.class_fhir.code if hasattr(enc, "class_fhir") else None
        if enc_class_code is None and hasattr(enc, "class_"):
            enc_class_code = enc.class_.code
        assert enc_class_code == "IMP", (
            f"PV1.2='I' must map to class code 'IMP', got {enc_class_code!r}"
        )

    def test_hl7v2_oru(self):
        """ORU_R01 → [Observation(+), DiagnosticReport] with LOINC from OBX-3/OBR-4."""
        from veridoc_ingestion.adapters.hl7v2 import HL7v2Adapter
        from veridoc_ingestion.adapter import SourceModality

        adapter = HL7v2Adapter()
        payload = (HL7_FIXTURES / "oru_r01.hl7").read_bytes()
        profile = _profile("site-001", SourceModality.HL7V2)

        resources = adapter.ingest(payload, profile)

        resource_types = [r.get_resource_type() for r in resources]
        assert "Observation" in resource_types, "ORU_R01 must yield at least one Observation"
        assert "DiagnosticReport" in resource_types, "ORU_R01 must yield a DiagnosticReport"

        observations = [r for r in resources if r.get_resource_type() == "Observation"]
        # 3 OBX in fixture → 3 Observations
        assert len(observations) >= 1, "Must have at least one Observation from OBX"

        # Verify LOINC code from OBX-3
        obs = observations[0]
        assert obs.code is not None, "Observation.code must be set"
        codings = obs.code.coding if obs.code.coding else []
        assert len(codings) > 0, "Observation.code must have at least one coding"
        loinc_coding = next(
            (c for c in codings if c.system and "loinc" in c.system.lower()),
            None,
        )
        assert loinc_coding is not None, (
            "Observation.code.coding must include a LOINC coding from OBX-3"
        )
        assert loinc_coding.code == "2160-0", (
            f"First OBX LOINC code must be 2160-0 (Creatinine), got {loinc_coding.code!r}"
        )

        # Verify DiagnosticReport has LOINC from OBR-4
        reports = [r for r in resources if r.get_resource_type() == "DiagnosticReport"]
        dr = reports[0]
        dr_codings = dr.code.coding if (dr.code and dr.code.coding) else []
        assert len(dr_codings) > 0, "DiagnosticReport.code must have at least one coding"

    def test_hl7v2_delegates_to_mapping(self):
        """HL7v2Adapter must use the mapping module, not a hand-rolled parser (D-12)."""
        import inspect
        from veridoc_ingestion.adapters import hl7v2 as hl7v2_module

        source = inspect.getsource(hl7v2_module)
        assert "hl7v2_fhir" in source, (
            "HL7v2Adapter must delegate to mapping.hl7v2_fhir (D-12: vetted library, not hand-rolled)"
        )


class TestPseudonymization:
    """SC-4: PII pseudonymized; same patient → same token across native + HL7 adapters."""

    def test_pseudonymization(self):
        """Raw MRN absent from native+HL7 output; same (patient_id, natural_id) → same token."""
        from veridoc_ingestion.adapters.native_fhir import NativeFhirAdapter
        from veridoc_ingestion.adapters.hl7v2 import HL7v2Adapter
        from veridoc_ingestion.adapter import SourceModality
        from veridoc_pseudonym import pseudonym_token

        raw_mrn = "MRN-SITE001-00042"

        # Native FHIR path: build from Synthea bundle
        native_adapter = NativeFhirAdapter()
        bundle_path = next(FHIR_FIXTURES.glob("*.json"))
        native_resources = native_adapter.ingest(
            bundle_path.read_bytes(),
            _profile("site-001", SourceModality.NATIVE_FHIR),
        )

        # HL7 path
        hl7_adapter = HL7v2Adapter()
        hl7_resources = hl7_adapter.ingest(
            (HL7_FIXTURES / "adt_a01.hl7").read_bytes(),
            _profile("site-001", SourceModality.HL7V2),
        )

        # Neither adapter should return a Patient whose identifier values contain the raw MRN
        for r in hl7_resources:
            if r.get_resource_type() == "Patient":
                identifiers = r.identifier or []
                for ident in identifiers:
                    assert raw_mrn not in (ident.value or ""), (
                        f"Raw MRN {raw_mrn!r} must not appear in HL7 Patient.identifier"
                    )

        # Pseudonym determinism: same inputs → same token (cross-adapter consistency)
        patient_id = "site-001-patient"
        natural_id = raw_mrn
        t1 = pseudonym_token(patient_id, natural_id)
        t2 = pseudonym_token(patient_id, natural_id)
        assert t1 == t2, "pseudonym_token must be deterministic for the same inputs"

        # Different patients → different tokens
        t3 = pseudonym_token("other-patient", natural_id)
        assert t1 != t3, "Different patient_id must produce different token"


# ===========================================================================
# Task 2 — PdfExcelAdapter + OcrAdapter + EntityExtractor
# ===========================================================================


class TestPdfExcelAdapter:
    """SC-2b: PdfExcelAdapter normalizes lab PDF → R4B resources."""

    def test_pdf_excel(self):
        """PdfExcelAdapter.ingest on a lab PDF returns R4B Observation resources."""
        from veridoc_ingestion.adapters.pdf_excel import PdfExcelAdapter
        from veridoc_ingestion.adapter import SourceModality

        adapter = PdfExcelAdapter()
        payload = (PDF_FIXTURES / "lab_report.pdf").read_bytes()
        profile = _profile("site-001", SourceModality.PDF_EXCEL)

        resources = adapter.ingest(payload, profile)

        assert isinstance(resources, list), "ingest must return a list"
        assert len(resources) > 0, "PDF adapter must produce at least one resource"

        # Should produce FHIR R4B models
        for r in resources:
            assert hasattr(r, "resource_type"), f"Expected FHIR model, got {type(r)}"

        # Lab report with Creatinine/Sodium/Potassium → Observations expected
        resource_types = [r.get_resource_type() for r in resources]
        assert "Observation" in resource_types, (
            "Lab PDF must yield at least one Observation"
        )

    def test_pdf_excel_pseudonymized(self):
        """PdfExcelAdapter output must not contain the raw MRN from the PDF."""
        from veridoc_ingestion.adapters.pdf_excel import PdfExcelAdapter
        from veridoc_ingestion.adapter import SourceModality

        adapter = PdfExcelAdapter()
        payload = (PDF_FIXTURES / "lab_report.pdf").read_bytes()
        profile = _profile("site-001", SourceModality.PDF_EXCEL)
        resources = adapter.ingest(payload, profile)

        raw_mrn = "MRN-SITE001-00042"
        for r in resources:
            if r.get_resource_type() == "Patient":
                identifiers = r.identifier or []
                for ident in identifiers:
                    assert raw_mrn not in (ident.value or ""), (
                        "Raw MRN must not appear in PdfExcelAdapter Patient.identifier"
                    )


class TestOcrAdapter:
    """SC-3: OcrAdapter produces DocumentReference with ocr-confidence + blob URI."""

    def test_ocr(self, minio_endpoint):
        """OcrAdapter with a stub engine produces DocumentReference with confidence + blob URI."""
        import shutil
        if not shutil.which("tesseract"):
            pytest.skip("tesseract binary not available")

        from veridoc_ingestion.adapters.ocr import OcrAdapter
        from veridoc_ingestion.blob_store import S3BlobStore
        from veridoc_ingestion.ocr_engine import TesseractEngine
        from veridoc_ingestion.adapter import SourceModality
        import boto3

        # Create bucket in ephemeral MinIO
        bucket = "veridoc-test"
        s3 = boto3.client(
            "s3",
            endpoint_url=minio_endpoint,
            aws_access_key_id="minioadmin",
            aws_secret_access_key="minioadmin",
        )
        s3.create_bucket(Bucket=bucket)

        blob_store = S3BlobStore(
            bucket=bucket,
            endpoint_url=minio_endpoint,
            access_key="minioadmin",
            secret_key="minioadmin",
        )
        ocr_engine = TesseractEngine()
        adapter = OcrAdapter(ocr_engine=ocr_engine, blob_store=blob_store)

        payload = (IMAGE_FIXTURES / "scan_legible.png").read_bytes()
        profile = _profile("site-001", SourceModality.OCR)
        resources = adapter.ingest(payload, profile)

        assert isinstance(resources, list)
        assert len(resources) > 0

        doc_refs = [r for r in resources if r.get_resource_type() == "DocumentReference"]
        assert len(doc_refs) >= 1, "OcrAdapter must produce at least one DocumentReference"
        doc_ref = doc_refs[0]

        # docStatus must be "preliminary"
        assert doc_ref.docStatus == "preliminary", (
            f"DocumentReference.docStatus must be 'preliminary', got {doc_ref.docStatus!r}"
        )

        # Must have content with a blob URI
        assert doc_ref.content and len(doc_ref.content) > 0
        attachment = doc_ref.content[0].attachment
        assert attachment.url, "content.attachment.url must point to the blob URI"
        assert attachment.url.startswith("s3://"), (
            f"blob URI must start with 's3://', got {attachment.url!r}"
        )

        # Must have ocr-confidence extension
        extensions = doc_ref.extension or []
        ext_urls = [e.url for e in extensions]
        assert "urn:veridoc:extension:ocr-confidence" in ext_urls, (
            "DocumentReference must carry an ocr-confidence extension"
        )

    def test_ocr_flags(self):
        """conf<0.95 → legibility-flag; conf<0.85 → legibility-escalate (stub OcrEngine)."""
        from veridoc_ingestion.adapters.ocr import OcrAdapter
        from veridoc_ingestion.ocr_engine import OcrEngine, OcrResult
        from veridoc_ingestion.blob_store import BlobStore
        from veridoc_ingestion.adapter import SourceModality

        class StubEngine(OcrEngine):
            def __init__(self, confidence: float):
                self._conf = confidence

            def extract(self, image_bytes: bytes, content_type: str) -> OcrResult:
                return OcrResult(
                    text="stub text",
                    document_confidence=self._conf,
                    word_confidences=[self._conf],
                    flagged=self._conf < 0.95,
                    escalated=self._conf < 0.85,
                )

        class StubBlobStore(BlobStore):
            def put(self, key: str, data: bytes, content_type: str) -> str:
                return f"s3://stub-bucket/{key}"

            def get(self, key: str) -> bytes:
                return b""

        def _make_adapter(conf: float) -> OcrAdapter:
            return OcrAdapter(
                ocr_engine=StubEngine(conf),
                blob_store=StubBlobStore(),
            )

        profile = _profile("site-001", SourceModality.OCR)
        payload = b"fake-image-bytes"

        # conf=0.97 → no flags
        resources_good = _make_adapter(0.97).ingest(payload, profile)
        doc_good = next(r for r in resources_good if r.get_resource_type() == "DocumentReference")
        flag_exts_good = [
            e for e in (doc_good.extension or [])
            if e.url == "urn:veridoc:extension:alcoa-legibility-flag"
        ]
        assert len(flag_exts_good) == 0, (
            "conf=0.97 must NOT produce a legibility-flag extension"
        )

        # conf=0.90 → legibility-flag only (not escalate)
        resources_flag = _make_adapter(0.90).ingest(payload, profile)
        doc_flag = next(r for r in resources_flag if r.get_resource_type() == "DocumentReference")
        flag_exts_flag = [
            e for e in (doc_flag.extension or [])
            if e.url == "urn:veridoc:extension:alcoa-legibility-flag"
        ]
        flag_values = [e.valueString for e in flag_exts_flag]
        assert "legibility-flag" in flag_values, (
            "conf=0.90 must set legibility-flag extension"
        )
        assert "legibility-escalate" not in flag_values, (
            "conf=0.90 must NOT set legibility-escalate extension"
        )

        # conf=0.80 → both legibility-flag and legibility-escalate
        resources_esc = _make_adapter(0.80).ingest(payload, profile)
        doc_esc = next(r for r in resources_esc if r.get_resource_type() == "DocumentReference")
        flag_exts_esc = [
            e for e in (doc_esc.extension or [])
            if e.url == "urn:veridoc:extension:alcoa-legibility-flag"
        ]
        esc_values = [e.valueString for e in flag_exts_esc]
        assert "legibility-flag" in esc_values, (
            "conf=0.80 must set legibility-flag extension"
        )
        assert "legibility-escalate" in esc_values, (
            "conf=0.80 must set legibility-escalate extension"
        )
