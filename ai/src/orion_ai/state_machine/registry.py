"""State machine registry."""

from orion_ai.state_machine.interfaces import ExperimentStateMachineInterface


class StateMachineRegistry:
    """Registry mapping experiment types to specialized state machines."""

    _engines: dict[str, type[ExperimentStateMachineInterface]] = {}

    @classmethod
    def register(cls, name: str, engine_cls: type[ExperimentStateMachineInterface]) -> None:
        cls._engines[name] = engine_cls

    @classmethod
    def get(cls, name: str) -> type[ExperimentStateMachineInterface]:
        if name not in cls._engines:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: State machine engine {name} is not registered."
            )
        return cls._engines[name]
