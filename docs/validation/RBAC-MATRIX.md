# RBAC Matrix — VeriDoc 8-Role Access Control (PLAT-03 / D-02)

> **Status:** Validation-ready evidence (GAMP 5 CSV / 21 CFR Part 11 §11.10(d), §11.10(g);
> EMA Annex 11 §12 access control). Change-controlled (DEC-gamp5-csv): this matrix and
> `deploy/keycloak/veridoc-realm.json` are the authoritative definition of the 8 roles and
> their access levels. Enforcement is **deny-by-default** — a role grants only what is
> listed here; everything else is denied (`veridoc_auth.require_role`).

The 8 roles are modeled as Keycloak realm roles (kebab-case) in the committed realm export
and surfaced in the access token's `realm_access.roles` claim. The API tier
(`veridoc-auth`) enforces them per-request as defence-in-depth at the resource boundary
(roles are defined in Keycloak; authorization is checked in the service).

## Roles

| # | Role (realm role) | Access level | Scope |
|---|-------------------|--------------|-------|
| 1 | Clinical Research Associate | `cra` | site-operational | Assigned sites |
| 2 | Data Manager | `data-manager` | study-data | Assigned studies |
| 3 | Medical Monitor | `medical-monitor` | study-clinical | Assigned studies |
| 4 | Site Coordinator | `site-coordinator` | site-operational | Own site only |
| 5 | Principal Investigator | `principal-investigator` | site-clinical | Own site only |
| 6 | Sponsor Representative | `sponsor-rep` | read-only-aggregate | Cross-site/study (read) |
| 7 | Regulatory Affairs | `regulatory-affairs` | audit-compliance | Cross-study (audit read) |
| 8 | System Administrator | `system-admin` | platform-admin | Platform-wide (no clinical authority) |

> **Tenancy note:** "Scope" above is enforced by `veridoc-tenancy` (request-scoped
> site/study context from the token's `site`/`study` claims, fail-closed — D-03). RBAC
> answers *"may this role perform this action?"*; tenancy answers *"on which site/study's
> data?"*. Both must pass.

## Resource × Action permission matrix

Legend: **F** = full (read + write), **R** = read-only, **W** = write-only (create/append),
**—** = no access. Every cell defaults to **—** unless granted below.

| Resource / Action | cra | data-manager | medical-monitor | site-coordinator | principal-investigator | sponsor-rep | regulatory-affairs | system-admin |
|-------------------|:---:|:------------:|:---------------:|:----------------:|:----------------------:|:-----------:|:------------------:|:------------:|
| **EMR source data** (read) | R | R | R | R (own site) | R (own site) | — | — | — |
| **eCRF / Rave data** (read) | R | F | R | R (own site) | R (own site) | R | — | — |
| **SDV findings / discrepancies** (review) | F | F | R | R | R | R | R | — |
| **Queries / discrepancy notes** (open/update/close) | F | F | R | W (respond, own site) | W (approve, own site) | — | — | — |
| **SAE / safety findings** (review + escalation) | R | R | F | R (own site) | R (own site) | R | R | — |
| **Risk-based monitoring scores** | R | R | R | — | — | R | R | — |
| **SDV reports / visit letters** | R | R | R | R (own site) | R (own site) | R | R | — |
| **Regulatory-submission reports** | — | — | R | — | — | R | F | — |
| **Audit trail** (immutable, append-only) | R (own actions) | R (own actions) | R (own actions) | R (own actions) | R (own actions) | R (own actions) | **F-read** (all) | R (config events) |
| **Tenant / study / site provisioning** | — | — | — | — | — | — | — | F |
| **Identity / realm administration** | — | — | — | — | — | — | — | F |
| **System configuration** | — | — | — | — | — | — | R | F |
| **PII re-identification** (decrypt) | — | — | — | — | — | — | — | — |

### Notes on distinct access levels (D-02 "distinct access levels")

- **CRA vs Site Coordinator** — both are site-operational, but the CRA works across *assigned
  sites* (monitoring) while the Site Coordinator is confined to *their own site* and acts as
  source-document custodian (responds to, rather than closes, queries).
- **Data Manager** — the broadest *data* write authority (study-level query lifecycle and data
  cleaning) but no clinical-decision authority.
- **Medical Monitor** — clinical oversight; the sole recipient of **all** SAE escalations
  (AESAE-01), with full safety-finding access but read-only on data operations.
- **Principal Investigator** — site clinical authority (signs off / approves resolutions for
  their own site) — a clinical superset of Site Coordinator within one site.
- **Sponsor Rep** — strictly **read-only aggregate** (dashboards/reports); never writes source
  data or queries (PORTAL-01 read-only Sponsor portal).
- **Regulatory Affairs** — the only role with **full read of the entire immutable audit trail**
  (Annex 11 audit-trail review) plus regulatory-report authority; no source-data write.
- **System Admin** — platform/identity/tenant administration with **no clinical-decision
  authority** — the human-in-the-loop constraint (DEC-human-in-the-loop) is preserved: no role,
  including admin, can auto-action a clinical decision, and **no role can re-identify PII**
  (decryption is a crypto-shred-governed, out-of-band operation, not an RBAC grant — D-11/D-12).

### Deny-by-default invariant

`veridoc_auth.require_role(*allowed)` raises **403** when the principal's `realm_access.roles`
contains none of the required roles. There is no implicit inheritance: a role sees exactly the
**F/R/W** cells in its column and nothing else. Cross-role access is proven blocked by
`libs/veridoc-auth/tests/test_rbac.py::test_cross_role_request_is_forbidden`.

## Traceability

| Control | Evidence |
|---------|----------|
| 8 roles defined with distinct access (D-02) | `deploy/keycloak/veridoc-realm.json` `roles.realm[]`; `libs/veridoc-auth/tests/test_realm_config.py::test_realm_declares_all_eight_roles` |
| Deny-by-default RBAC enforced in API tier | `libs/veridoc-auth/src/veridoc_auth/rbac.py`; `test_rbac.py` |
| MFA enforced (acr/amr) | realm `browser-mfa` REQUIRED OTP flow + `acr.loa.map`; `veridoc-auth` middleware acr assertion; `test_jwt_verify.py::test_token_without_mfa_is_rejected` |
| Tenancy scoping (site/study) | `veridoc-tenancy` fail-closed context (D-03); `test_tenancy_failclosed.py` |
| Audit-trail review (Annex 11) | `regulatory-affairs` full audit read row above; audit log immutability from plan 01-02 |
