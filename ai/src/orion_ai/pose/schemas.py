"""Human pose estimation schemas."""

from pydantic import BaseModel, Field

from orion_ai.detection.schemas import BoundingBox2D


class Keypoint2D(BaseModel):
    """2D keypoint coordinate with confidence."""

    id: int
    name: str
    x: float
    y: float
    score: float = Field(ge=0.0, le=1.0)


class Keypoint3D(BaseModel):
    """3D keypoint relative to camera or root joint in meters."""

    id: int
    name: str
    x: float
    y: float
    z: float
    score: float = Field(ge=0.0, le=1.0)


class HumanPose(BaseModel):
    """Estimated skeleton for an individual subject."""

    person_id: int
    bbox: BoundingBox2D
    topology: str = "coco_17"
    keypoints_2d: list[Keypoint2D]
    keypoints_3d: list[Keypoint3D] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0.0, le=1.0)

    @property
    def keypoints(self) -> list[Keypoint2D]:
        """Convenience accessor for 2D keypoints."""
        return self.keypoints_2d


class PoseEstimationResult(BaseModel):
    """Batch pose estimation results for a frame."""

    frame_index: int
    poses: list[HumanPose]
    inference_time_ms: float
