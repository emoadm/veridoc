"""0001 — append-only audit_log table + immutability trigger (D-04/D-05/D-06).

Creates ``audit_log`` with every D-06 column INCLUDING the nullable ``agent_decision``
(jsonb) and ``agent_confidence`` (numeric) fields, so the append-only table never needs a
later migration when Phase 4 agents begin writing them. Adds a BEFORE UPDATE OR DELETE
trigger that RAISES on any attempt to mutate or remove a row (immutability — threat
T-02-01), plus a comment documenting that the application DB role should hold INSERT/SELECT
only (least privilege, belt-and-suspenders for 21 CFR Part 11).

Usable two ways:
* as an Alembic revision (``upgrade()`` / ``downgrade()`` via ``alembic.op``);
* directly against a SQLAlchemy ``Connection`` (``apply(conn)`` / ``revert(conn)``), used
  by the test fixture which has no full Alembic env.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

# --- Alembic identifiers -----------------------------------------------------------
revision = "0001_audit_log"
down_revision = None
branch_labels = None
depends_on = None


# --- DDL ----------------------------------------------------------------------------

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    prev_hash       varchar(64) NOT NULL,
    record_hash     varchar(64) NOT NULL UNIQUE,
    actor_id        text        NOT NULL,
    actor_role      text        NOT NULL,
    tenant_id       text        NOT NULL,
    action          text        NOT NULL,
    entity_type     text        NOT NULL,
    entity_id       text        NOT NULL,
    before          jsonb,
    after           jsonb,
    -- D-06: nullable agent fields declared NOW (avoid migrating an append-only table later).
    agent_decision  jsonb,
    agent_confidence numeric,
    occurred_at     timestamptz NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);
"""

# Index supporting the chain-head read (ORDER BY id DESC LIMIT 1) and the verify walk.
_CREATE_INDEX = "CREATE INDEX IF NOT EXISTS ix_audit_log_id ON audit_log (id);"

# Immutability: any UPDATE or DELETE on a persisted audit row is rejected (T-02-01).
_CREATE_TRIGGER_FN = """
CREATE OR REPLACE FUNCTION audit_log_reject_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: % is not permitted', TG_OP
        USING ERRCODE = 'check_violation';
END;
$$ LANGUAGE plpgsql;
"""

_CREATE_TRIGGER = """
CREATE TRIGGER audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_reject_mutation();
"""

# Least-privilege documentation (belt-and-suspenders for Part 11). The deployed app role
# should hold INSERT/SELECT only; UPDATE/DELETE are additionally blocked by the trigger.
_COMMENT = (
    "COMMENT ON TABLE audit_log IS "
    "'Append-only tamper-evident audit trail (D-04/D-05/D-06). "
    "App DB role MUST hold INSERT/SELECT only (least privilege). "
    "UPDATE/DELETE are rejected by trigger audit_log_immutable.';"
)

_DROP = [
    "DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log;",
    "DROP FUNCTION IF EXISTS audit_log_reject_mutation();",
    "DROP TABLE IF EXISTS audit_log;",
]


def apply(connection: Connection) -> None:
    """Apply the migration directly against a SQLAlchemy connection (used by tests)."""
    connection.execute(text(_CREATE_TABLE))
    connection.execute(text(_CREATE_INDEX))
    connection.execute(text(_CREATE_TRIGGER_FN))
    connection.execute(text(_CREATE_TRIGGER))
    connection.execute(text(_COMMENT))


def revert(connection: Connection) -> None:
    for stmt in _DROP:
        connection.execute(text(stmt))


def upgrade() -> None:  # pragma: no cover - exercised only under a full Alembic env
    from alembic import op

    apply(op.get_bind())


def downgrade() -> None:  # pragma: no cover
    from alembic import op

    revert(op.get_bind())
