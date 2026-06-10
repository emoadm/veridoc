"""veridoc_audit — shared tamper-evident audit SDK (PLAT-02, D-04/D-05/D-06).

Public API (Task 1 — pure functions, no DB):

* :func:`canonicalize` — RFC 8785 JCS canonical bytes for a payload (deterministic).
* :func:`compute_record_hash` — ``SHA-256(prev_hash || JCS(payload))``.
* :func:`verify_chain` — re-walk a chain of row mappings; ``False`` if broken/tampered.

The DB-backed writer (:func:`append_audit`), the :class:`AuditEvent` model, and the
``Session``-aware :func:`verify_chain` overload are added in Task 2 (``sdk.py`` / ``models.py``).
"""

from __future__ import annotations

from .chain import compute_record_hash, verify_chain
from .jcs import canonicalize

__all__ = [
    "canonicalize",
    "compute_record_hash",
    "verify_chain",
]
