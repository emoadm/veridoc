"""Per-site SourceProfileRegistry: register, resolve, and route ingestion requests.

The registry maps ``site_id`` → ``SourceProfile`` and then maps the profile's
``modality`` → the concrete ``SourceAdapter`` subclass to instantiate. This keeps
the routing logic in the shared lib rather than the service tier (see RESEARCH.md
Architectural Responsibility Map).

Pattern analog: ``veridoc-auth/allowlist.py`` (data-driven per-tenant lookup).

Concrete adapter classes are registered in ``_MODALITY_ADAPTER_MAP`` below.
Four real adapter implementations (NativeFhirAdapter, HL7v2Adapter, PdfExcelAdapter,
OcrAdapter) are added by plan 02-05; only ProprietaryAdapter is wired here.
"""

from __future__ import annotations

from .adapter import SourceAdapter, SourceModality, SourceProfile

__all__ = ["SourceProfileRegistry"]


def _build_modality_map() -> dict[SourceModality, type[SourceAdapter]]:
    """Build the module-level modality → adapter-class table.

    Imports are deferred (inside this function) so that missing optional
    dependencies in partial installs do not break the import of this module.
    The four real adapters are wired by plan 02-05; only PROPRIETARY is live now.
    """
    from .adapters.proprietary import ProprietaryAdapter

    return {
        SourceModality.PROPRIETARY: ProprietaryAdapter,
        # 02-05 will add:
        # SourceModality.NATIVE_FHIR: NativeFhirAdapter,
        # SourceModality.HL7V2:       HL7v2Adapter,
        # SourceModality.PDF_EXCEL:   PdfExcelAdapter,
        # SourceModality.OCR:         OcrAdapter,
    }


_MODALITY_ADAPTER_MAP: dict[SourceModality, type[SourceAdapter]] | None = None


def _get_modality_map() -> dict[SourceModality, type[SourceAdapter]]:
    global _MODALITY_ADAPTER_MAP
    if _MODALITY_ADAPTER_MAP is None:
        _MODALITY_ADAPTER_MAP = _build_modality_map()
    return _MODALITY_ADAPTER_MAP


class SourceProfileRegistry:
    """Per-site profile registry: register once, resolve by site_id at ingest time.

    Thread-safety: ``register`` and ``get`` are dict reads/writes; the GIL makes
    these atomic for CPython, which is sufficient for the single-writer (startup)
    / multiple-reader (per-request) pattern used in the ingestion-service.
    """

    def __init__(self) -> None:
        self._profiles: dict[str, SourceProfile] = {}

    def register(self, profile: SourceProfile) -> None:
        """Register a per-site source profile.

        Later registrations with the same ``site_id`` overwrite earlier ones;
        callers should register each site exactly once at startup.

        Args:
            profile: The ``SourceProfile`` to register.
        """
        self._profiles[profile.site_id] = profile

    def get(self, site_id: str) -> SourceProfile:
        """Resolve the ``SourceProfile`` for a site.

        Args:
            site_id: The clinical-site identifier.

        Returns:
            The registered ``SourceProfile``.

        Raises:
            LookupError: When no profile has been registered for ``site_id``.
                         (Not a bare ``KeyError`` — contains the unknown site_id.)
        """
        try:
            return self._profiles[site_id]
        except KeyError:
            registered = list(self._profiles.keys())
            raise LookupError(
                f"No SourceProfile registered for site_id={site_id!r}. "
                f"Registered sites: {registered}"
            ) from None

    def get_adapter(self, site_id: str) -> SourceAdapter:
        """Resolve and instantiate the concrete adapter for a site.

        Looks up the ``SourceProfile`` for ``site_id``, maps its ``modality``
        to a concrete ``SourceAdapter`` subclass via the module-level table,
        and returns a new instance.

        Args:
            site_id: The clinical-site identifier.

        Returns:
            A concrete ``SourceAdapter`` instance for the site's modality.

        Raises:
            LookupError: When the site has no registered profile.
            NotImplementedError: When the modality has no concrete adapter yet.
        """
        profile = self.get(site_id)
        modality_map = _get_modality_map()
        adapter_class = modality_map.get(profile.modality)
        if adapter_class is None:
            raise NotImplementedError(
                f"No SourceAdapter registered for modality={profile.modality!r}. "
                f"Available modalities: {list(modality_map.keys())}"
            )
        return adapter_class()
