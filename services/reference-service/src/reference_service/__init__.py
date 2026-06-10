"""reference_service — the one walking-skeleton FastAPI service (D-07).

A thin tenancy-scoped Subject create/update endpoint that exercises authn -> authz ->
tenancy -> envelope-encrypted PII + deterministic pseudonym -> same-transaction hash-chained
audit -> Postgres, end to end. ``create_app`` builds the FastAPI app; ``main:app`` is the
uvicorn entrypoint.
"""

from .main import app, create_app

__all__ = ["app", "create_app"]
