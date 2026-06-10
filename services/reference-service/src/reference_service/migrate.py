"""Migration loader/runner for the reference service.

The migration modules live in ``services/reference-service/migrations/`` (outside the wheel
``src/`` tree, mirroring the veridoc-audit lib layout) so they ship as DDL artifacts, not
importable package code. This module loads them by path and applies them in dependency order
(audit_log first, then subject) — used by the service startup path and the test fixture,
neither of which runs a full Alembic env. CI (plan 01-06) drives the same DDL via Alembic.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

# services/reference-service/  (two levels up from src/reference_service/migrate.py is
# src/reference_service; the service root is three levels up).
_SERVICE_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _SERVICE_ROOT / "migrations"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


# The reference-service subject migration (this plan).
subject_migration = _load(
    "reference_service._subject_migration_0001", _MIGRATIONS_DIR / "0001_subject.py"
)

# The veridoc-audit append-only audit_log migration (plan 01-02), loaded from the lib.
import veridoc_audit  # noqa: E402

_AUDIT_MIGRATION_PATH = (
    Path(veridoc_audit.__file__).resolve().parents[2] / "migrations" / "0001_audit_log.py"
)
audit_migration = _load("reference_service._audit_migration_0001", _AUDIT_MIGRATION_PATH)

__all__ = ["audit_migration", "subject_migration", "apply_all", "revert_all"]


def apply_all(connection) -> None:
    """Apply both migrations in dependency order (audit_log, then subject)."""
    audit_migration.apply(connection)
    subject_migration.apply(connection)


def revert_all(connection) -> None:
    """Revert both migrations in reverse order (subject, then audit_log)."""
    subject_migration.revert(connection)
    audit_migration.revert(connection)
