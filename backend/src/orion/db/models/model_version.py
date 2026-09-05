"""SQLAlchemy ORM model for certified AI model weights registry."""

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from orion.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ModelVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Certified AI flight model metadata and checksum registration."""

    __tablename__ = "model_versions"

    model_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    subsystem: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # detection, pose, har
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    framework: Mapped[str] = mapped_column(String(32), nullable=False)  # onnx, tensorrt, openvino
    precision: Mapped[str] = mapped_column(String(16), nullable=False)  # fp32, fp16, int8

    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    flight_certified: Mapped[bool] = mapped_column(default=False, nullable=False)

    metadata_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
