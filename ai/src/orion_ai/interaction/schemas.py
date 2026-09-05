"""Human-Object Interaction (HOI) schemas."""

from pydantic import BaseModel, Field

from orion_ai.detection.schemas import DetectionTarget
from orion_ai.pose.schemas import HumanPose


class SpatialRelation(BaseModel):
    """Spatial 3D/2D distance and vector between person and object."""

    distance_px: float
    relative_angle_rad: float
    iou_overlap: float = 0.0


class InteractionTriplet(BaseModel):
    """Subject-Predicate-Object HOI triplet (e.g. Astronaut Holds Pipette)."""

    subject_id: int
    object_id: int
    subject_class: str = "astronaut"
    object_class: str
    action_predicate: str  # e.g. "holds", "operates", "inspects", "adjusts"
    confidence: float = Field(ge=0.0, le=1.0)
    spatial: SpatialRelation


class InteractionResult(BaseModel):
    """Interaction analysis result for a frame."""

    frame_index: int
    triplets: list[InteractionTriplet]
    active_poses: list[HumanPose]
    active_objects: list[DetectionTarget]
