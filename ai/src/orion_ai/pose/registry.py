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
        if not cls._estimators:
            from orion_ai.pose.yolo_pose import YOLOPoseEstimator

            cls.register("yolo11_pose", YOLOPoseEstimator)
            cls.register("rtmpose", YOLOPoseEstimator)
            cls.register("baseline_pose", YOLOPoseEstimator)

        if name not in cls._estimators:
            raise NotImplementedError(f"NOT IMPLEMENTED: Pose estimator {name} is not registered.")
        return cls._estimators[name]
