"""RBAC + cross-tenant denial against the live verify path (T-05-03).

- a token for a permitted role (site-coordinator) can POST /subjects (2xx);
- a token for a non-permitted role (regulatory-affairs) gets 403 (deny-by-default);
- a token scoped to tenant X cannot read/write a subject created under tenant Y (denied).
"""

from __future__ import annotations


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_permitted_role_can_create(client, make_token):
    token = make_token(sub="coord", roles=["site-coordinator"], site="site-001", study="study-A")
    resp = client.post("/subjects", json={"natural_id": "MRN-1", "pii": "P"}, headers=_auth(token))
    assert resp.status_code == 201, resp.text


def test_nonpermitted_role_gets_403(client, make_token):
    # regulatory-affairs is a valid realm role but NOT a Subject-write role.
    token = make_token(sub="ra", roles=["regulatory-affairs"], site="site-001", study="study-A")
    resp = client.post("/subjects", json={"natural_id": "MRN-2", "pii": "P"}, headers=_auth(token))
    assert resp.status_code == 403, resp.text


def test_cross_tenant_update_is_denied(client, make_token):
    # Create a subject under tenant site-001/study-A.
    token_a = make_token(sub="coord-a", roles=["data-manager"], site="site-001", study="study-A")
    created = client.post(
        "/subjects", json={"natural_id": "MRN-3", "pii": "P"}, headers=_auth(token_a)
    )
    assert created.status_code == 201, created.text
    subject_id = created.json()["id"]

    # A caller in a DIFFERENT tenant (site-002/study-B) must not update it.
    token_b = make_token(sub="coord-b", roles=["data-manager"], site="site-002", study="study-B")
    resp = client.put(f"/subjects/{subject_id}", json={"pii": "Hacked"}, headers=_auth(token_b))
    assert resp.status_code == 403, resp.text


def test_missing_mfa_is_rejected(client, make_token):
    # A token that did not complete MFA is rejected at the edge (T-05-05).
    token = make_token(
        sub="coord", roles=["site-coordinator"], site="site-001", study="study-A", mfa=False
    )
    resp = client.post("/subjects", json={"natural_id": "MRN-4", "pii": "P"}, headers=_auth(token))
    assert resp.status_code == 401, resp.text
