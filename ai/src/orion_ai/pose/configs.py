"""Pose configuration schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class PoseConfig(BaseModel):
    """Configuration contract for pose estimation models."""

    model_id: str
    topology: Literal["coco_17", "halpe_26", "wholebody_133"] = "coco_17"
    keypoint_score_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    enable_3d: bool = False
    batch_size: int = Field(default=1, ge=1)
