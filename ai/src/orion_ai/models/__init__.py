"""Models registry subsystem package."""

from orion_ai.models.configs import ModelRegistryConfig
from orion_ai.models.interfaces import (
    ModelRegistryInterface,
    ModelWeightsLoaderInterface,
)
from orion_ai.models.registry import ModelCatalogRegistry
from orion_ai.models.schemas import (
    ChecksumManifest,
    ModelMetadata,
    QuantizationProfile,
)

__all__ = [
    "ChecksumManifest",
    "ModelCatalogRegistry",
    "ModelMetadata",
    "ModelRegistryConfig",
    "ModelRegistryInterface",
    "ModelWeightsLoaderInterface",
    "QuantizationProfile",
]
