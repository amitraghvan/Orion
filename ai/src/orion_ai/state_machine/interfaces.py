"""Experiment state machine interfaces."""

from abc import ABC, abstractmethod
from typing import Any

from orion_ai.state_machine.schemas import ExperimentStateSnapshot


class ExperimentStateMachineInterface(ABC):
    """Abstract contract for deterministic flight experiment step validation."""

    @abstractmethod
    def initialize_experiment(self, experiment_spec: dict[str, Any]) -> None:
        """Parse YAML specification and initialize state graph."""
        raise NotImplementedError(
            "NOT IMPLEMENTED: ExperimentStateMachineInterface.initialize_experiment"
        )

    @abstractmethod
    def evaluate_step(self, frame_events: list[Any]) -> ExperimentStateSnapshot:
        """Ingest AI perception outputs and update active step status."""
        raise NotImplementedError("NOT IMPLEMENTED: ExperimentStateMachineInterface.evaluate_step")

    @abstractmethod
    def reset(self) -> None:
        """Reset state machine to pre-experiment state."""
        raise NotImplementedError("NOT IMPLEMENTED: ExperimentStateMachineInterface.reset")
