"""SQLAlchemy 2.x engine + session factory (one session per request).

The session boundary matters for D-05: the business write and its hash-chained audit row
share ONE transaction. The request handler opens a session, performs the Subject write,
calls ``append_audit`` on the SAME session (which never commits), and commits once at the
end — so the business row and the audit row are atomic.
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
    """Yield a request-scoped Session, rolling back on error and closing afterward.

    The handler owns the commit (D-05): on success the handler calls ``session.commit()``;
    on any exception this scope rolls back so the business write AND its audit row both
    vanish (atomicity, Pitfall 5).
    """
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
