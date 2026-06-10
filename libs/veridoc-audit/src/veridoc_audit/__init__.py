"""veridoc_audit — shared tamper-evident audit SDK (PLAT-02, D-04/D-05/D-06).

Public API:

* :func:`canonicalize` — RFC 8785 JCS canonical bytes for a payload (deterministic).
* :func:`compute_record_hash` — ``SHA-256(prev_hash || JCS(payload))``.
* :func:`verify_chain` — re-walk a chain; ``False`` if broken/tampered. Accepts either an
  in-memory iterable of row mappings or a live SQLAlchemy ``Session`` (DB-backed walk).
* :func:`append_audit` — write one append-only, advisory-locked audit row inside the
  CALLER's open transaction (no internal commit), returning its ``record_hash``.
* :class:`AuditEvent` — the D-06 event payload (identity/role/tenant/action/before/after
  + nullable agent decision/confidence).
* :class:`AuditLog` — the SQLAlchemy mapped class for the ``audit_log`` table.

The pure chain/JCS functions have no DB dependency; the DB-backed writer/verifier live in
``sdk.py`` / ``models.py``.
"""

from __future__ import annotations

from .chain import compute_record_hash
from .chain import verify_chain as _verify_chain_rows
from .jcs import canonicalize
from .models import AuditEvent, AuditLog
from .sdk import append_audit
from .sdk import verify_chain as _verify_chain_session

__all__ = [
    "canonicalize",
    "compute_record_hash",
    "verify_chain",
    "append_audit",
    "AuditEvent",
    "AuditLog",
]


def verify_chain(source):
    """Verify a hash chain, dispatching on ``source``.

    * a SQLAlchemy ``Session`` (exposes ``execute``) → walk the persisted ``audit_log``
      rows in ``id`` order (DB-backed, :func:`sdk.verify_chain`);
    * any other iterable of row mappings → walk in memory (:func:`chain.verify_chain`).
    """
    if hasattr(source, "execute"):
        return _verify_chain_session(source)
    return _verify_chain_rows(source)
