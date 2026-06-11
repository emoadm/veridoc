"""SQLAlchemy 2.x engine + session factory for the ingestion-service.

Cloned verbatim from ``services/reference-service/src/reference_service/db.py``.
The session boundary matters for the "ingest:enqueued" audit write: the handler
opens a session, enqueues the RQ job, calls ``append_audit`` on the SAME session,
and commits once (D-05 — business enqueue + audit row atomic).

The worker's "ingest:completed" audit write follows D-06 deviation: the worker opens
its own session via ``veridoc_ingestion.worker._session_scope`` (not this file).
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


def make_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for ``database_url`` (defaults to settings)."""
    url = database_url or get_settings().database_url
    return create_engine(url, future=True, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory bound to ``engine`` (one Session per request)."""
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield a request-scoped Session; rollback on error, always close.

    The handler owns the commit (D-05).
    """
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
