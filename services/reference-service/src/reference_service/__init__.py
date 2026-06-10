"""reference_service — the one walking-skeleton FastAPI service (skeleton).

Implemented in plan 01-05: a thin tenancy-scoped Subject create/update endpoint that
exercises authn -> authz -> tenancy -> envelope-encrypted PII + deterministic
pseudonym -> same-transaction hash-chained audit, end to end (D-07).
"""
