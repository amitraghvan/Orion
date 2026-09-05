"""Training and fine-tuning schemas."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TrainingBatch(BaseModel):
    """Batch data representation for training loops."""

    batch_idx: int
    batch_size: int
    sample_ids: list[str]


class CheckpointMetadata(BaseModel):
    """Saved training checkpoint properties."""

    checkpoint_path: Path
    epoch: int
    step: int
    validation_loss: float
    best_metric: float
    is_best: bool = False


class TrainingRunMetrics(BaseModel):
    """Aggregated metrics history across epochs."""

    run_id: str
    total_epochs: int
    epoch_losses: list[float]
    metrics_history: dict[str, list[float]] = Field(default_factory=dict)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
