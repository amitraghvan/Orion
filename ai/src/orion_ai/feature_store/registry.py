"""Feature store registry."""

from orion_ai.feature_store.interfaces import FeatureStoreInterface


class FeatureStoreRegistry:
    """Registry mapping vector store backends to implementation classes."""

    _stores: dict[str, type[FeatureStoreInterface]] = {}

    @classmethod
    def register(cls, backend_name: str, store_cls: type[FeatureStoreInterface]) -> None:
        cls._stores[backend_name] = store_cls

    @classmethod
    def get(cls, backend_name: str) -> type[FeatureStoreInterface]:
        if backend_name not in cls._stores:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Feature store backend {backend_name} is not registered."
            )
        return cls._stores[backend_name]
