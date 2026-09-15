"""SQLAlchemy ORM model for protocol validation decisions and evidence audit trail."""

from typing import Any

from sqlalchemy import JSON, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProtocolDecisionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted protocol decision event with cryptographically linked evidence."""

    __tablename__ = "protocol_decisions"

    decision_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    experiment_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    step_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    observed_action: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_actions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    entropy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    debounce_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    debounce_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    retroactive_skips: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
