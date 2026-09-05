"""SQLAlchemy ORM model for video recording segments."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from orion.db.models.run import Run


class Recording(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Archival record of an experiment video segment."""

    __tablename__ = "recordings"

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    frame_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fps: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    codec: Mapped[str] = mapped_column(String(32), nullable=False, default="h264")

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="recordings")
