"""SQLAlchemy ORM model for experiment execution runs."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from orion.db.models.alert import Alert
    from orion.db.models.event import Event
    from orion.db.models.experiment import Experiment
    from orion.db.models.recording import Recording
    from orion.db.models.step import Step


class Run(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An execution run instance of a scientific experiment."""

    __tablename__ = "runs"

    experiment_id: Mapped[UUID] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    station_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="INITIATED", index=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    telemetry_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="runs")
    steps: Mapped[list["Step"]] = relationship(
        "Step", back_populates="run", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(
        "Event", back_populates="run", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="run", cascade="all, delete-orphan"
    )
    recordings: Mapped[list["Recording"]] = relationship(
        "Recording", back_populates="run", cascade="all, delete-orphan"
    )
