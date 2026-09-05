"""SQLAlchemy ORM model for domain and telemetry events."""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from orion.db.models.run import Run


class Event(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent audit log of domain and telemetry events."""

    __tablename__ = "events"

    run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="SYSTEM")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Relationships
    run: Mapped["Run | None"] = relationship("Run", back_populates="events")
