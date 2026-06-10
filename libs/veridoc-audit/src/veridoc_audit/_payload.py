"""Shared hash-payload construction.

The bytes hashed into the chain MUST be reproducible: a row written by ``append_audit``
has to re-hash to its stored ``record_hash`` when :func:`sdk.verify_chain` reads it back.
That requires every value to round-trip through Postgres identically. Two values need care:

* ``occurred_at`` — normalized to a UTC, microsecond-precision ISO-8601 string. A naive
  datetime is treated as UTC; an aware datetime is converted to UTC. Postgres ``timestamptz``
  stores in UTC and returns an aware UTC datetime, so write-time and read-time strings match.
* ``agent_confidence`` — normalized to ``float`` (it round-trips as ``Decimal`` from
  Postgres ``numeric``).

This module is the single source of truth used by both :meth:`AuditEvent.hash_payload`
and ``sdk._row_hash_payload`` so the two can never drift.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

__all__ = ["normalize_occurred_at", "normalize_confidence", "build_hash_payload"]


def normalize_occurred_at(value: datetime) -> str:
    """Return a UTC, microsecond-precision ISO-8601 string for ``value``."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def normalize_confidence(value: float | Decimal | None) -> float | None:
    return float(value) if value is not None else None


def build_hash_payload(
    *,
    actor_id: str,
    actor_role: str,
    tenant_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    agent_decision: dict[str, Any] | None,
    agent_confidence: float | Decimal | None,
    occurred_at: datetime,
) -> dict[str, Any]:
    """Assemble the deterministic dict that the chain hashes (server columns excluded)."""
    return {
        "actor_id": actor_id,
        "actor_role": actor_role,
        "tenant_id": tenant_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before": before,
        "after": after,
        "agent_decision": agent_decision,
        "agent_confidence": normalize_confidence(agent_confidence),
        "occurred_at": normalize_occurred_at(occurred_at),
    }
