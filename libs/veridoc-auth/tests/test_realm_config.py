"""Structural validation of the committed Keycloak realm-as-code export.

The realm JSON (``deploy/keycloak/veridoc-realm.json``) is loaded by Keycloak via
``--import-realm`` (RESEARCH Pitfall 4 — realm config in version control). These tests
are the change-control guard: they fail in CI if the realm export drifts from the
contract that ``veridoc-auth`` / ``veridoc-tenancy`` depend on (8 roles, an MFA-required
auth flow, an OIDC confidential client with an audience mapper).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# deploy/keycloak/veridoc-realm.json lives at the repo root, four parents up from this file:
#   libs/veridoc-auth/tests/test_realm_config.py -> repo root
_REALM_PATH = (
    Path(__file__).resolve().parents[3] / "deploy" / "keycloak" / "veridoc-realm.json"
)

# The 8 PLAT-03 / D-02 roles in their kebab-case realm-role form.
_REQUIRED_ROLES = {
    "cra",
    "data-manager",
    "medical-monitor",
    "site-coordinator",
    "principal-investigator",
    "sponsor-rep",
    "regulatory-affairs",
    "system-admin",
}


@pytest.fixture(scope="module")
def realm() -> dict:
    assert _REALM_PATH.exists(), f"realm export missing at {_REALM_PATH}"
    with _REALM_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def test_realm_is_valid_json_named_veridoc(realm: dict) -> None:
    assert realm.get("realm") == "veridoc"


def test_realm_declares_all_eight_roles(realm: dict) -> None:
    declared = {r["name"] for r in realm["roles"]["realm"]}
    missing = _REQUIRED_ROLES - declared
    assert not missing, f"realm missing roles: {sorted(missing)}"


def test_realm_has_oidc_confidential_client_with_audience_mapper(realm: dict) -> None:
    clients = {c["clientId"]: c for c in realm.get("clients", [])}
    assert "reference-service" in clients, "missing reference-service OIDC client"
    client = clients["reference-service"]
    # Confidential client = not public + has client-authn enabled.
    assert client.get("publicClient") is False
    # An audience protocol mapper so the access token's `aud` matches the client.
    mappers = client.get("protocolMappers", [])
    has_audience = any(
        m.get("protocolMapper") == "oidc-audience-mapper" for m in mappers
    )
    assert has_audience, "reference-service client lacks an oidc-audience-mapper"


def test_realm_has_required_mfa_otp_flow(realm: dict) -> None:
    """Some authentication flow must include a REQUIRED OTP/MFA step so tokens carry acr/amr=mfa."""
    flows = realm.get("authenticationFlows", [])
    required_otp = []
    for flow in flows:
        for execution in flow.get("authenticationExecutions", []):
            authenticator = execution.get("authenticator", "")
            requirement = execution.get("requirement", "")
            if "otp" in authenticator.lower() and requirement == "REQUIRED":
                required_otp.append((flow.get("alias"), authenticator))
    assert required_otp, "no REQUIRED OTP/MFA execution found in any authentication flow"


def test_realm_carries_acr_loa_map_for_mfa(realm: dict) -> None:
    """An acr->LoA mapping (or browser flow acr) so issued tokens expose acr=mfa."""
    attrs = realm.get("attributes", {})
    acr_map = attrs.get("acr.loa.map")
    assert acr_map, "realm lacks acr.loa.map attribute (acr claim wiring for MFA)"
    assert "mfa" in acr_map, "acr.loa.map does not define an 'mfa' level"


def test_realm_sets_session_timeouts(realm: dict) -> None:
    """Session management (D-02 / V3): idle + max session lifespans are set."""
    assert isinstance(realm.get("ssoSessionIdleTimeout"), int)
    assert isinstance(realm.get("ssoSessionMaxLifespan"), int)
    assert realm["ssoSessionMaxLifespan"] > 0
