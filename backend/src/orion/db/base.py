"""SQLAlchemy 2.0 Declarative Base and aerospace audit mixins."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Root declarative base for all ORION database entities."""


class UUIDPrimaryKeyMixin:
    """Provides a primary key UUID formatted as string for cross-engine compatibility."""

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        sort_order=-10,
    )


class TimestampMixin:
    """Provides standard aerospace UTC audit timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )
