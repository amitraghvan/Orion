"""SQLAlchemy ORM model for individual experiment execution steps."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from orion.db.models.run import Run


class Step(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution state of a single step within an experiment run."""

    __tablename__ = "steps"

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    validation_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="steps")
