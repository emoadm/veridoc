"""Wave 0 smoke test — ensures `uv run pytest` collects at least one test.

Real audit-chain tests (chain, tamper-detection, same-txn, JCS golden vector) land
in plan 01-02. This placeholder keeps the Wave 0 harness green from a clean clone.
"""

import veridoc_audit


def test_package_importable():
    assert veridoc_audit is not None


def test_smoke():
    assert True
