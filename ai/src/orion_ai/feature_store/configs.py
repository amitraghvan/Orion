"""Feature store configuration schemas."""

from pydantic import BaseModel, Field


class FeatureStoreConfig(BaseModel):
    """Configuration contract for offline vector store."""

    backend: str = "sqlite_vec"  # sqlite_vec, memory, faiss
    storage_path: str = "./data/feature_store.db"
    vector_dimension: int = Field(default=512, ge=16)
    distance_metric: str = "cosine"
