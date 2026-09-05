"""Evaluation configuration schemas."""

from pydantic import BaseModel, Field


class EvaluationConfig(BaseModel):
    """Configuration contract for model evaluation benchmark."""

    metrics: list[str] = Field(default_factory=lambda: ["mAP50", "mAP50-95", "latency"])
    iou_thresholds: list[float] = Field(default_factory=lambda: [0.5, 0.75, 0.9])
    compute_confusion_matrix: bool = True
    save_predictions: bool = False
