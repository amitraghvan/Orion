"""Runtime executor registry."""

from orion_ai.runtime.interfaces import RuntimeExecutorInterface


class RuntimeRegistry:
    """Registry mapping pipeline modes to executor implementations."""

    _executors: dict[str, type[RuntimeExecutorInterface]] = {}

    @classmethod
    def register(cls, mode: str, executor_cls: type[RuntimeExecutorInterface]) -> None:
        cls._executors[mode] = executor_cls

    @classmethod
    def get(cls, mode: str) -> type[RuntimeExecutorInterface]:
        if mode not in cls._executors:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Runtime executor for mode {mode} is not registered."
            )
        return cls._executors[mode]
