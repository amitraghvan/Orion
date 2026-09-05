"""Runtime scheduling interfaces."""

from abc import ABC, abstractmethod
from typing import Any

from orion_ai.runtime.schemas import (
    ExecutionContext,
    PipelineTask,
    RuntimePerformance,
)


class PipelineSchedulerInterface(ABC):
    """Interface for topological DAG ordering of perception tasks."""

    @abstractmethod
    def build_schedule(self, tasks: list[PipelineTask]) -> list[PipelineTask]:
        """Compute valid execution order respecting latency budgets and dependencies."""
        raise NotImplementedError("NOT IMPLEMENTED: PipelineSchedulerInterface.build_schedule")


class RuntimeExecutorInterface(ABC):
    """Interface for coordinating sequential and parallel perception execution."""

    @abstractmethod
    async def execute_cycle(
        self, frame_buffer: Any, ctx: ExecutionContext
    ) -> tuple[dict[str, Any], RuntimePerformance]:
        """Run entire perception DAG for one optical frame."""
        raise NotImplementedError("NOT IMPLEMENTED: RuntimeExecutorInterface.execute_cycle")
