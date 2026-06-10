"""Unit tests for the pure hash-chain functions (D-04).

No DB required — exercises compute_record_hash and verify_chain over in-memory rows.
Covers: key-order independence, the SHA-256(prev || JCS(payload)) definition, an intact
chain verifying True, and a mutated/broken-link chain verifying False (the in-memory
analogue of the DB-backed tamper-detection gate).
"""

import hashlib

from veridoc_audit import canonicalize, compute_record_hash, verify_chain


def _row(prev_hash: str, payload: dict) -> dict:
    return {
        "prev_hash": prev_hash,
        "record_hash": compute_record_hash(prev_hash, payload),
        "payload": payload,
    }


def _build_chain(payloads: list[dict]) -> list[dict]:
    rows: list[dict] = []
    prev = ""  # genesis prev_hash is the empty string
    for payload in payloads:
        row = _row(prev, payload)
        rows.append(row)
        prev = row["record_hash"]
    return rows


def test_key_order_independence():
    assert canonicalize({"a": 1, "b": 2}) == canonicalize({"b": 2, "a": 1})


def test_compute_record_hash_definition():
    """record_hash == sha256(prev.encode() + canonicalize(payload)).hexdigest()."""
    prev = "deadbeef"
    payload = {"action": "create", "n": 7}
    expected = hashlib.sha256(prev.encode() + canonicalize(payload)).hexdigest()
    assert compute_record_hash(prev, payload) == expected


def test_genesis_prev_hash_is_empty_string():
    payload = {"action": "genesis"}
    assert compute_record_hash("", payload) == hashlib.sha256(canonicalize(payload)).hexdigest()


def test_verify_chain_intact_returns_true():
    rows = _build_chain([{"i": 0}, {"i": 1}, {"i": 2}])
    assert verify_chain(rows) is True


def test_verify_chain_tampered_payload_returns_false():
    """Mutating a prior row's payload (without recomputing its hash) breaks the chain."""
    rows = _build_chain([{"i": 0}, {"i": 1}, {"i": 2}])
    rows[1]["payload"] = {"i": 99}  # tamper: payload no longer hashes to record_hash
    assert verify_chain(rows) is False


def test_verify_chain_broken_link_returns_false():
    """Forging a prev_hash link (forked chain) is detected."""
    rows = _build_chain([{"i": 0}, {"i": 1}, {"i": 2}])
    rows[2]["prev_hash"] = "0" * 64  # broken link: doesn't match prior record_hash
    assert verify_chain(rows) is False


def test_verify_chain_empty_is_true():
    assert verify_chain([]) is True
