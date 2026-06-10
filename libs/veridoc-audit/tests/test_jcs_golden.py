"""Golden-vector test for RFC 8785 JCS canonicalization + hash (D-04, Pitfall 2).

A committed known input -> known canonical bytes -> known hex digest. This test FAILS
in CI if the canonicalization drifts (dependency bump, library swap), which would
otherwise surface as false tamper positives when the chain is re-walked. This is the
guard mandated by RESEARCH Pitfall 2.
"""

from veridoc_audit import canonicalize, compute_record_hash

# --- Committed golden vectors (rfc8785 0.1.4, Trail of Bits) -----------------------
# canonicalize sorts keys by UTF-16 code unit, emits no insignificant whitespace, and
# UTF-8 encodes the result. "é" (U+00E9) serialises to its raw UTF-8 bytes 0xC3 0xA9.
GOLDEN_PAYLOAD = {"b": 1, "a": 2, "u": "é"}
GOLDEN_CANONICAL_BYTES = b'{"a":2,"b":1,"u":"\xc3\xa9"}'
GOLDEN_GENESIS_HASH = "85c1ca334228cf725dc3e862cb52d03ea88924bb1226a63927856fb77a0911e4"


def test_canonicalize_golden_bytes():
    """A known payload always produces the same canonical byte string."""
    assert canonicalize(GOLDEN_PAYLOAD) == GOLDEN_CANONICAL_BYTES


def test_canonicalize_returns_bytes():
    assert isinstance(canonicalize(GOLDEN_PAYLOAD), bytes)


def test_compute_record_hash_golden_digest():
    """Genesis hash (prev_hash == "") of the golden payload is byte-stable."""
    assert compute_record_hash("", GOLDEN_PAYLOAD) == GOLDEN_GENESIS_HASH


def test_canonicalize_sorts_keys_by_codepoint():
    """Keys are emitted in canonical order regardless of insertion order."""
    assert canonicalize({"b": 1, "a": 2, "u": "é"}) == GOLDEN_CANONICAL_BYTES
