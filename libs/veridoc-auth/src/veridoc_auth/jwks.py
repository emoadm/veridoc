"""JWKS fetch + cache, keyed by ``kid`` (RESEARCH Pattern 2).

Keycloak publishes its signing keys at ``{issuer}/protocol/openid-connect/certs``. The
auth middleware needs the *public* RSA key matching a token's ``kid`` header to verify the
RS256 signature. This module:

- parses a JWKS document (Keycloak shape) via ``jwcrypto`` into per-``kid`` public keys;
- caches them with a TTL so we don't fetch on every request;
- exposes a no-network constructor (``from_public_keys``) used by tests and by callers that
  already hold the keys.

Network fetching uses the stdlib ``urllib`` (no new HTTP dependency); a live Keycloak
round-trip is exercised in plan 01-05. Rotation is handled by re-fetching when an unknown
``kid`` is seen (and the cache has expired).
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Any

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwcrypto import jwk

from .errors import AuthError


class JWKSCache:
    """Caches Keycloak JWKS public keys keyed by ``kid``.

    Parameters
    ----------
    jwks_uri:
        The JWKS endpoint (``.../protocol/openid-connect/certs``). May be ``None`` for an
        offline cache built via :meth:`from_public_keys`.
    ttl_seconds:
        How long fetched keys stay fresh before a re-fetch is allowed.
    """

    def __init__(self, jwks_uri: str | None = None, ttl_seconds: int = 600) -> None:
        self._jwks_uri = jwks_uri
        self._ttl = ttl_seconds
        self._keys: dict[str, RSAPublicKey] = {}
        self._fetched_at: float = 0.0
        self._lock = threading.Lock()

    # -- constructors ---------------------------------------------------------

    @classmethod
    def from_public_keys(cls, keys: dict[str, RSAPublicKey]) -> JWKSCache:
        """Build an offline cache from already-resolved ``{kid: public_key}`` (tests)."""
        inst = cls(jwks_uri=None)
        inst._keys = dict(keys)
        inst._fetched_at = time.monotonic()
        return inst

    @classmethod
    def from_jwks_document(cls, document: dict[str, Any]) -> JWKSCache:
        """Build an offline cache from a parsed JWKS JSON document (Keycloak shape)."""
        inst = cls(jwks_uri=None)
        inst._keys = _parse_jwks(document)
        inst._fetched_at = time.monotonic()
        return inst

    # -- lookup ---------------------------------------------------------------

    def get_key(self, kid: str) -> RSAPublicKey:
        """Return the public key for ``kid``, fetching/refreshing if needed.

        Raises :class:`AuthError` when the ``kid`` cannot be resolved (unknown signer).
        """
        key = self._keys.get(kid)
        if key is not None:
            return key
        # Unknown kid: refresh once (handles key rotation) if we have an endpoint.
        if self._jwks_uri is not None and self._is_stale():
            self._refresh()
            key = self._keys.get(kid)
            if key is not None:
                return key
        raise AuthError(f"no signing key for kid={kid!r}")

    # -- internals ------------------------------------------------------------

    def _is_stale(self) -> bool:
        return (time.monotonic() - self._fetched_at) >= self._ttl

    def _refresh(self) -> None:
        assert self._jwks_uri is not None
        with self._lock:
            try:
                with urllib.request.urlopen(self._jwks_uri, timeout=5) as resp:  # noqa: S310
                    document = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:  # pragma: no cover - network path (plan 01-05)
                raise AuthError(f"failed to fetch JWKS: {exc}") from exc
            self._keys = _parse_jwks(document)
            self._fetched_at = time.monotonic()


def _parse_jwks(document: dict[str, Any]) -> dict[str, RSAPublicKey]:
    """Parse a JWKS document into ``{kid: RSAPublicKey}``, keeping only signing keys."""
    out: dict[str, RSAPublicKey] = {}
    for entry in document.get("keys", []):
        # Only RSA signing keys are relevant for RS256 verification.
        if entry.get("kty") != "RSA":
            continue
        use = entry.get("use")
        if use is not None and use != "sig":
            continue
        kid = entry.get("kid")
        if not kid:
            continue
        key = jwk.JWK(**entry)
        pem = key.export_to_pem()
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        public_key = load_pem_public_key(pem)
        if isinstance(public_key, RSAPublicKey):
            out[kid] = public_key
    return out
