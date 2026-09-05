"""Model catalog registry."""

from orion_ai.models.schemas import ModelMetadata


class ModelCatalogRegistry:
    """In-memory model catalog registry."""

    _catalog: dict[str, ModelMetadata] = {}

    @classmethod
    def register(cls, model_id: str, metadata: ModelMetadata) -> None:
        cls._catalog[model_id] = metadata

    @classmethod
    def get(cls, model_id: str) -> ModelMetadata:
        if model_id not in cls._catalog:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Model {model_id} metadata is not found in registry."
            )
        return cls._catalog[model_id]

    @classmethod
    def all_models(cls) -> list[ModelMetadata]:
        return list(cls._catalog.values())
