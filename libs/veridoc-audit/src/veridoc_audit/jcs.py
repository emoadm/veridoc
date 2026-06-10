"""RFC 8785 JSON Canonicalization Scheme (JCS) for the audit hash payload.

Determinism is a correctness requirement: the audit hash chain hashes the canonical
bytes of each payload, so canonicalization MUST be byte-stable across runs, Python
versions, and library upgrades. A non-deterministic payload produces false tamper
positives when the chain is re-walked (RESEARCH Pitfall 2).

We delegate to the ``rfc8785`` package (Trail of Bits, ``github.com/trailofbits/rfc8785.py``),
adjudicated *authentic — approved* in ``docs/validation/PACKAGE-LEGITIMACY.md`` (RESEARCH
Open Question #4 / A4). No in-house JCS fallback is needed. The committed golden-vector
test (``tests/test_jcs_golden.py``) guards against any serialization drift.
"""

from __future__ import annotations

import rfc8785

__all__ = ["canonicalize"]


def canonicalize(payload: dict) -> bytes:
    """Return the RFC 8785 canonical UTF-8 byte serialization of ``payload``.

    The output is independent of key insertion order (keys are emitted sorted by their
    UTF-16 code units), carries no insignificant whitespace, and uses canonical number
    formatting — the deterministic input the hash chain depends on.
    """
    return rfc8785.dumps(payload)
