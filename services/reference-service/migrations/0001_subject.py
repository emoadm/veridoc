"""0001 — the reference ``subject`` table (D-07 walking skeleton).

A tenancy-scoped synthetic Subject:
  - ``tenant_id`` (``site/study``) stamped from ``current_tenant()`` (fail-closed);
  - ``pseudonym_token`` — the deterministic per-patient token (veridoc-pseudonym);
  - ``pii_ciphertext`` (bytea) — envelope-encrypted PII at rest (veridoc-crypto); NEVER
    plaintext (T-05-04).

Usable two ways (mirroring the audit migration):
* as an Alembic revision (``upgrade()`` / ``downgrade()``);
* directly against a SQLAlchemy ``Connection`` (``apply(conn)`` / ``revert(conn)``), used by
  the test fixture and the service startup path which have no full Alembic env.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

# --- Alembic identifiers ----------------------------------------------------------------
revision = "0001_subject"
# The audit_log table (veridoc-audit 0001) is applied first; declared as the parent so a
# full Alembic env orders them correctly.
down_revision = "0001_audit_log"
branch_labels = None
depends_on = None


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS subject (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       text        NOT NULL,
    pseudonym_token varchar(64) NOT NULL,
    pii_ciphertext  bytea       NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
"""

# Indexes supporting tenancy-scoped lookups + pseudonym joins.
_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_subject_tenant_id ON subject (tenant_id);",
    "CREATE INDEX IF NOT EXISTS ix_subject_pseudonym_token ON subject (pseudonym_token);",
]

_DROP = [
    "DROP TABLE IF EXISTS subject;",
]


def apply(connection: Connection) -> None:
    """Apply the migration directly against a SQLAlchemy connection (tests / startup)."""
    connection.execute(text(_CREATE_TABLE))
    for stmt in _CREATE_INDEXES:
        connection.execute(text(stmt))


def revert(connection: Connection) -> None:
    for stmt in _DROP:
        connection.execute(text(stmt))


def upgrade() -> None:  # pragma: no cover - exercised only under a full Alembic env
    from alembic import op

    apply(op.get_bind())


def downgrade() -> None:  # pragma: no cover
    from alembic import op

    revert(op.get_bind())
