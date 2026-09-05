"""Pose estimator registry."""

from orion_ai.pose.interfaces import PoseEstimatorInterface


class PoseEstimatorRegistry:
    """Registry mapping pose estimator algorithms to implementation classes."""

    _estimators: dict[str, type[PoseEstimatorInterface]] = {}

    @classmethod
    def register(cls, name: str, estimator_cls: type[PoseEstimatorInterface]) -> None:
        cls._estimators[name] = estimator_cls

    @classmethod
    def get(cls, name: str) -> type[PoseEstimatorInterface]:
        if name not in cls._estimators:
            raise NotImplementedError(f"NOT IMPLEMENTED: Pose estimator {name} is not registered.")
        return cls._estimators[name]
