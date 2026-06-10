"""Per-record SHA-256 hash chain (D-04).

Each audit record stores ``record_hash = SHA-256(prev_hash || JCS(payload))`` where
``prev_hash`` is the previous record's hash (the empty string for the genesis record).
Tampering with any prior record — mutating its payload or forging a link — is detectable
by re-walking the chain with :func:`verify_chain`.

These are pure functions (no DB). The DB-backed writer/verifier in ``sdk.py`` builds on
them; the in-memory tests in ``tests/test_chain.py`` exercise them directly.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping

from .jcs import canonicalize

__all__ = ["compute_record_hash", "verify_chain"]


def compute_record_hash(prev_hash: str, payload: dict) -> str:
    """Compute ``SHA-256(prev_hash || JCS(payload))`` as a hex digest.

    ``prev_hash`` is the empty string ``""`` for the genesis record. The canonical bytes
    of ``payload`` (RFC 8785) are appended to the UTF-8 bytes of ``prev_hash``.
    """
    return hashlib.sha256(prev_hash.encode("utf-8") + canonicalize(payload)).hexdigest()


def verify_chain(rows: Iterable[Mapping]) -> bool:
    """Re-walk an ordered sequence of audit rows; return ``True`` iff the chain is intact.

    Each row must expose ``prev_hash``, ``record_hash`` and ``payload`` (mapping access).
    Rows MUST be supplied in chain order (genesis first). The walk fails closed:

    * a ``prev_hash`` that does not match the running predecessor hash → broken link;
    * a ``record_hash`` that does not equal the recomputed hash of its payload → tampered.

    An empty chain is trivially intact.
    """
    prev = ""  # genesis predecessor
    for row in rows:
        if row["prev_hash"] != prev:
            return False  # broken / forked link
        if compute_record_hash(prev, row["payload"]) != row["record_hash"]:
            return False  # payload tampered (or hash forged)
        prev = row["record_hash"]
    return True
