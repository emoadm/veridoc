"""Tests for SourceAdapter ABC, SourceProfile, SourceProfileRegistry, and ProprietaryAdapter.

RED phase: these tests are written before the implementation exists and MUST fail.
GREEN phase: implementation in adapter.py, registry.py, adapters/proprietary.py makes them pass.
"""

from __future__ import annotations

import abc

import pytest


def test_source_modality_is_strenum() -> None:
    """SourceModality must be a StrEnum with all five members."""
    from veridoc_ingestion.adapter import SourceModality

    expected = {"NATIVE_FHIR", "HL7V2", "PDF_EXCEL", "OCR", "PROPRIETARY"}
    assert expected <= {m.name for m in SourceModality}
    # Must behave as a string
    assert SourceModality.NATIVE_FHIR == "native-fhir"
    assert SourceModality.HL7V2 == "hl7v2"
    assert SourceModality.PDF_EXCEL == "pdf-excel"
    assert SourceModality.OCR == "ocr"
    assert SourceModality.PROPRIETARY == "proprietary"


def test_source_adapter_is_abstract() -> None:
    """SourceAdapter must be an abc.ABC with an abstract ingest method."""
    from veridoc_ingestion.adapter import SourceAdapter

    assert issubclass(SourceAdapter, abc.ABC)
    # Cannot instantiate the abstract class
    with pytest.raises(TypeError):
        SourceAdapter()  # type: ignore[abstract]


def test_source_profile_is_frozen_dataclass() -> None:
    """SourceProfile must be a frozen dataclass with site_id, modality, config."""
    from veridoc_ingestion.adapter import SourceModality, SourceProfile

    profile = SourceProfile(
        site_id="site-001",
        modality=SourceModality.NATIVE_FHIR,
        config={"fhir_version": "R4B"},
    )
    assert profile.site_id == "site-001"
    assert profile.modality == SourceModality.NATIVE_FHIR
    assert profile.config == {"fhir_version": "R4B"}

    # Frozen: mutation must raise
    with pytest.raises((AttributeError, TypeError)):
        profile.site_id = "changed"  # type: ignore[misc]


def test_registry_register_and_get() -> None:
    """SourceProfileRegistry.register + get returns the correct profile."""
    from veridoc_ingestion.adapter import SourceModality, SourceProfile
    from veridoc_ingestion.registry import SourceProfileRegistry

    registry = SourceProfileRegistry()
    profile = SourceProfile(
        site_id="site-001",
        modality=SourceModality.OCR,
        config={"dpi": 300},
    )
    registry.register(profile)
    retrieved = registry.get("site-001")
    assert retrieved is profile


def test_registry_unknown_site_raises_descriptive_error() -> None:
    """Unknown site_id lookup must raise a descriptive error, not a bare KeyError."""
    from veridoc_ingestion.registry import SourceProfileRegistry

    registry = SourceProfileRegistry()
    with pytest.raises(Exception, match="site-unknown") as exc_info:
        registry.get("site-unknown")
    # Must NOT be a bare KeyError (which gives no context)
    assert type(exc_info.value).__name__ != "KeyError"


def test_registry_get_adapter_proprietary() -> None:
    """get_adapter for PROPRIETARY modality returns a ProprietaryAdapter."""
    from veridoc_ingestion.adapter import SourceModality, SourceProfile
    from veridoc_ingestion.adapters.proprietary import ProprietaryAdapter
    from veridoc_ingestion.registry import SourceProfileRegistry

    registry = SourceProfileRegistry()
    profile = SourceProfile(
        site_id="site-proprietary",
        modality=SourceModality.PROPRIETARY,
        config={},
    )
    registry.register(profile)
    adapter = registry.get_adapter("site-proprietary")
    assert isinstance(adapter, ProprietaryAdapter)


def test_proprietary_adapter_ingest_raises_not_implemented() -> None:
    """ProprietaryAdapter.ingest must raise NotImplementedError with a wire-when message."""
    from veridoc_ingestion.adapter import SourceModality, SourceProfile
    from veridoc_ingestion.adapters.proprietary import ProprietaryAdapter

    adapter = ProprietaryAdapter()
    profile = SourceProfile(
        site_id="site-001",
        modality=SourceModality.PROPRIETARY,
        config={},
    )
    with pytest.raises(NotImplementedError, match="wire"):
        adapter.ingest(b"payload", profile)


def test_proprietary_adapter_conforms_to_source_adapter() -> None:
    """ProprietaryAdapter must be a subclass of SourceAdapter (D-11)."""
    from veridoc_ingestion.adapter import SourceAdapter
    from veridoc_ingestion.adapters.proprietary import ProprietaryAdapter

    assert issubclass(ProprietaryAdapter, SourceAdapter)
