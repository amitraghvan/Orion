"""Trainer registry."""

from orion_ai.training.interfaces import TrainingLoopInterface


class TrainerRegistry:
    """Registry mapping training algorithms to implementation classes."""

    _trainers: dict[str, type[TrainingLoopInterface]] = {}

    @classmethod
    def register(cls, name: str, trainer_cls: type[TrainingLoopInterface]) -> None:
        cls._trainers[name] = trainer_cls

    @classmethod
    def get(cls, name: str) -> type[TrainingLoopInterface]:
        if name not in cls._trainers:
            raise NotImplementedError(f"NOT IMPLEMENTED: Trainer {name} is not registered.")
        return cls._trainers[name]
