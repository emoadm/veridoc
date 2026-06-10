"""Audit data model (D-06).

* :class:`AuditEvent` — the Pydantic v2 payload a caller hands to :func:`append_audit`.
  Carries identity/role/tenant/action/before/after plus the *nullable* AI-agent decision
  and confidence fields (D-06), declared now so the append-only ``audit_log`` table never
  needs a later migration when Phase 4 starts writing them.
* :class:`AuditLog` — the SQLAlchemy 2.x mapped class for the ``audit_log`` table.

The bytes that feed the hash chain are derived from a deterministic *hash payload*
(:meth:`AuditEvent.hash_payload`), NOT from the whole row — server-assigned columns
(``id``, ``created_at``) are excluded so the hash is reproducible during verification.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    DateTime,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ._payload import build_hash_payload

__all__ = ["AuditEvent", "AuditLog", "Base"]


class Base(DeclarativeBase):
    """Declarative base for the audit SDK's mapped classes."""


class AuditEvent(BaseModel):
    """A single auditable action (D-06).

    ``before``/``after`` carry already-pseudonymized / encrypted values supplied by the
    caller — the audit SDK is value-agnostic (threat T-02-06: PII handling is the caller's
    contract, see plan 03 helpers). ``agent_decision``/``agent_confidence`` are nullable
    now and consumed by Phase 4 agents.
    """

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    actor_role: str
    tenant_id: str
    action: str
    entity_type: str
    entity_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    agent_decision: dict[str, Any] | None = None
    agent_confidence: float | None = None
    occurred_at: datetime

    def hash_payload(self) -> dict[str, Any]:
        """The deterministic payload hashed into the chain.

        Excludes server-assigned columns (``id``, ``created_at``) so the hash is
        reproducible at verification time. Built via the shared ``_payload`` helper so it
        can never drift from the row-side reconstruction in ``sdk._row_hash_payload``.
        """
        return build_hash_payload(
            actor_id=self.actor_id,
            actor_role=self.actor_role,
            tenant_id=self.tenant_id,
            action=self.action,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            before=self.before,
            after=self.after,
            agent_decision=self.agent_decision,
            agent_confidence=self.agent_confidence,
            occurred_at=self.occurred_at,
        )


class AuditLog(Base):
    """Append-only audit row. Mutating any persisted row is blocked by a DB trigger
    (immutability) and detectable by re-walking the hash chain."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    actor_role: Mapped[str] = mapped_column(String, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # D-06: nullable agent fields declared NOW to avoid migrating an append-only table.
    agent_decision: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    agent_confidence: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
