"""SQLAlchemy ORM model for versioned flight datasets."""

from typing import Any

from sqlalchemy import JSON, BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DatasetVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Archival dataset manifest version entity."""

    __tablename__ = "dataset_versions"

    dataset_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    version_tag: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False)  # coco, yolo, mmpose, parquet
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_manifest: Mapped[str] = mapped_column(String(64), nullable=False)

    split_distribution: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    class_statistics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
