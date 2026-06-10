"""Reference-service ORM models (D-07 walking skeleton).

The :class:`Subject` is the deliberately-thin reference business entity (RESEARCH Open
Question #3): a tenancy-scoped synthetic patient whose write exercises authn -> authz ->
tenancy -> audited write -> encrypted persistence without pulling in later-phase domain
logic. PII lives only as ``pii_ciphertext`` (envelope ciphertext, veridoc-crypto); the
patient identity at rest is the deterministic ``pseudonym_token`` (veridoc-pseudonym).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for the reference-service mapped classes."""


class Subject(Base):
    """A tenancy-scoped synthetic Subject.

    ``pii_ciphertext`` is envelope-encrypted at rest (never plaintext); ``pseudonym_token``
    is the deterministic per-patient token and doubles as the crypto/pseudonym patient_id.
    ``tenant_id`` (``site/study``) is stamped from ``current_tenant()`` — fail-closed.
    """

    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    pseudonym_token: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pii_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
