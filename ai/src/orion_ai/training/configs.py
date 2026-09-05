"""Training configuration schemas."""

from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """Configuration contract for model training and fine-tuning."""

    experiment_name: str
    epochs: int = Field(default=100, ge=1)
    batch_size: int = Field(default=16, ge=1)
    learning_rate: float = Field(default=1e-4, gt=0.0)
    optimizer: str = "AdamW"
    weight_decay: float = 1e-2
    seed: int = 42
    mixed_precision: bool = True
