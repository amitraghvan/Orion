"""Feature store interfaces."""

from abc import ABC, abstractmethod

from orion_ai.feature_store.schemas import (
    EntityFeatures,
    FeatureQuery,
    FeatureVector,
)


class FeatureStoreInterface(ABC):
    """Interface for offline embedding cache and vector similarity search."""

    @abstractmethod
    async def put_features(self, entity_id: str, features: EntityFeatures) -> None:
        """Store spatial-temporal embedding for an entity."""
        raise NotImplementedError("NOT IMPLEMENTED: FeatureStoreInterface.put_features")

    @abstractmethod
    async def get_features(self, entity_id: str) -> EntityFeatures | None:
        """Retrieve stored feature vector."""
        raise NotImplementedError("NOT IMPLEMENTED: FeatureStoreInterface.get_features")

    @abstractmethod
    async def query_nearest(self, query: FeatureQuery) -> list[tuple[FeatureVector, float]]:
        """Find top-K nearest neighbors using cosine/Euclidean distance."""
        raise NotImplementedError("NOT IMPLEMENTED: FeatureStoreInterface.query_nearest")
