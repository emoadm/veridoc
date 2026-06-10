"""Data-driven, per-tenant IP-allowlisting hook (D-02; T-04-07).

This is a **hook**, not a hard-coded IP list: the allowlist is supplied as data keyed by
tenant (site/study), so policy lives in configuration/the data layer rather than in code.
Semantics are opt-in / fail-open-when-unset:

- no allowlist configured for the tenant  -> allow (the hook is inactive for that tenant);
- an allowlist configured                 -> allow only if the client IP is in one of the
  listed CIDR ranges, else :class:`AuthError` (deny).

Full allowlist-policy enforcement (mandatory per-tenant, default-deny) is a later hardening
(threat T-04-07 disposition = *accept* this phase); this wires the data-driven seam so the
reference service and later phases can enforce without code changes.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Mapping, Sequence

from .errors import AuthError

# An allowlist maps a tenant key (e.g. site id) to the CIDR ranges permitted for it.
AllowlistMap = Mapping[str, Sequence[str]]


def ip_allowlist_check(
    client_ip: str,
    *,
    tenant: str,
    allowlists: AllowlistMap,
) -> None:
    """Enforce the per-tenant IP allowlist (data-driven hook).

    Raises :class:`AuthError` when an allowlist exists for ``tenant`` and ``client_ip`` is
    not within any of its CIDR ranges. Allows (returns ``None``) when no allowlist is
    configured for the tenant.
    """
    ranges = allowlists.get(tenant)
    if not ranges:
        # No policy for this tenant -> hook inactive -> allow.
        return

    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError as exc:
        raise AuthError(f"invalid client IP {client_ip!r}") from exc

    for cidr in ranges:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as exc:  # pragma: no cover - misconfiguration guard
            raise AuthError(f"invalid allowlist CIDR {cidr!r} for tenant {tenant!r}") from exc
        if addr in network:
            return

    raise AuthError(f"client IP {client_ip} not in the allowlist for tenant {tenant!r}")
