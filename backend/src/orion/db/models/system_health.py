"""SQLAlchemy ORM model for periodic system health telemetry."""

from typing import Any

from sqlalchemy import JSON, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SystemHealth(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Subsystem health snapshots logged for reliability auditing."""

    __tablename__ = "system_health"

    station_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    subsystem: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    cpu_usage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_usage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    gpu_usage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)

    telemetry_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
