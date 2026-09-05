"""Model loader and registry interfaces."""

from abc import ABC, abstractmethod
from pathlib import Path

from orion_ai.models.schemas import ModelMetadata


class ModelWeightsLoaderInterface(ABC):
    """Interface for downloading, verifying checksum, and mounting weights."""

    @abstractmethod
    async def fetch_and_verify(self, metadata: ModelMetadata, target_dir: Path) -> Path:
        """Verify hash digest and return verified file path."""
        raise NotImplementedError("NOT IMPLEMENTED: ModelWeightsLoaderInterface.fetch_and_verify")


class ModelRegistryInterface(ABC):
    """Interface for querying certified models."""

    @abstractmethod
    def get_model_metadata(self, model_id: str) -> ModelMetadata:
        """Fetch flight metadata specification."""
        raise NotImplementedError("NOT IMPLEMENTED: ModelRegistryInterface.get_model_metadata")

    @abstractmethod
    def list_certified_models(self) -> list[ModelMetadata]:
        """List all models certified for flight deployment."""
        raise NotImplementedError("NOT IMPLEMENTED: ModelRegistryInterface.list_certified_models")
