"""Dataset specification schemas supporting COCO, YOLO, CVAT, Label Studio, MMPose, CSV, Parquet."""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# COCO Schema
# ------------------------------------------------------------------------------
class COCOImage(BaseModel):
    id: int
    width: int
    height: int
    file_name: str


class COCOCategory(BaseModel):
    id: int
    name: str
    supercategory: str | None = None


class COCOAnnotation(BaseModel):
    id: int
    image_id: int
    category_id: int
    bbox: list[float]  # [x, y, width, height]
    area: float
    iscrowd: int = 0
    keypoints: list[float] | None = None  # [x, y, v, ...] for pose


class COCODataset(BaseModel):
    info: dict[str, Any] = Field(default_factory=dict)
    licenses: list[dict[str, Any]] = Field(default_factory=list)
    images: list[COCOImage]
    annotations: list[COCOAnnotation]
    categories: list[COCOCategory]


# ------------------------------------------------------------------------------
# YOLO Schema
# ------------------------------------------------------------------------------
class YOLOAnnotation(BaseModel):
    class_id: int
    x_center: float = Field(ge=0.0, le=1.0)
    y_center: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)


# ------------------------------------------------------------------------------
# MMPose Schema
# ------------------------------------------------------------------------------
class MMPoseAnnotation(BaseModel):
    image_id: int
    category_id: int
    keypoints: list[list[float]]  # [[x, y, score], ...]
    box: list[float]  # [x, y, w, h]


# ------------------------------------------------------------------------------
# CVAT & Label Studio
# ------------------------------------------------------------------------------
class CVATBox(BaseModel):
    label: str
    xtl: float
    ytl: float
    xbr: float
    ybr: float
    occluded: int = 0


class LabelStudioResult(BaseModel):
    id: str
    from_name: str
    to_name: str
    type: str
    value: dict[str, Any]


# ------------------------------------------------------------------------------
# Tabular / Parquet / Metadata Schema
# ------------------------------------------------------------------------------
class DatasetMetadata(BaseModel):
    """Archival dataset metadata."""

    dataset_name: str
    version: str
    format: Literal["coco", "yolo", "cvat", "label_studio", "mmpose", "parquet", "csv"]
    total_images: int
    total_annotations: int
    classes: list[str]
    air_gapped_verified: bool = True
    sha256_checksum: str
