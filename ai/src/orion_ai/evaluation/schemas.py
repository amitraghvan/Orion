"""Model evaluation and metrics schemas."""

from pydantic import BaseModel, Field


class MetricResult(BaseModel):
    """Calculated metric entry."""

    metric_name: str  # mAP50, mAP50-95, PCK, accuracy, f1_score
    value: float
    per_class_values: dict[str, float] = Field(default_factory=dict)


class ConfusionMatrixData(BaseModel):
    """Confusion matrix representation for multi-class classification."""

    class_labels: list[str]
    matrix: list[list[int]]


class BenchmarkSummary(BaseModel):
    """Holistic model evaluation summary."""

    model_id: str
    dataset_version: str
    metrics: list[MetricResult]
    confusion_matrix: ConfusionMatrixData | None = None
    mean_inference_time_ms: float
    p99_inference_time_ms: float
