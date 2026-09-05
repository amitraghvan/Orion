"""Activity classifier registry."""

from orion_ai.activity.interfaces import ActivityClassifierInterface


class ActivityRegistry:
    """Registry mapping HAR models to classifier implementations."""

    _classifiers: dict[str, type[ActivityClassifierInterface]] = {}

    @classmethod
    def register(cls, name: str, classifier_cls: type[ActivityClassifierInterface]) -> None:
        cls._classifiers[name] = classifier_cls

    @classmethod
    def get(cls, name: str) -> type[ActivityClassifierInterface]:
        if name not in cls._classifiers:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Activity classifier {name} is not registered."
            )
        return cls._classifiers[name]
