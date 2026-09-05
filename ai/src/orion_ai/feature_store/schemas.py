"""Feature store schemas for spatial and temporal embeddings."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class FeatureVector(BaseModel):
    """Dense embedding representation."""

    vector_id: str
    dimension: int
    values: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityFeatures(BaseModel):
    """Aggregated features for a detected astronaut, tool, or experiment step."""

    entity_id: str
    entity_type: str  # astronaut, tool, experiment_step
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    features: dict[str, FeatureVector] = Field(default_factory=dict)


class FeatureQuery(BaseModel):
    """Nearest neighbor search query."""

    query_vector: list[float]
    top_k: int = Field(default=5, ge=1)
    filter_metadata: dict[str, Any] = Field(default_factory=dict)
