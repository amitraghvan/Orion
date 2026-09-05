"""SQLAlchemy ORM model for scientific experiments."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from orion.db.models.run import Run


class Experiment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Scientific experiment specification registry."""

    __tablename__ = "experiments"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE", index=True)

    # Raw YAML/JSON definition storage
    specification: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Associated execution runs
    runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="experiment", cascade="all, delete-orphan"
    )
