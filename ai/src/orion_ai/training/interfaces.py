"""Training interfaces."""

from abc import ABC, abstractmethod
from pathlib import Path

from orion_ai.training.schemas import (
    CheckpointMetadata,
    TrainingRunMetrics,
)


class TrainingLoopInterface(ABC):
    """Interface for microgravity transfer learning and fine-tuning."""

    @abstractmethod
    async def run_training(self) -> TrainingRunMetrics:
        """Execute full training epoch cycle."""
        raise NotImplementedError("NOT IMPLEMENTED: TrainingLoopInterface.run_training")


class CheckpointManagerInterface(ABC):
    """Interface for atomic weight checkpoint saving and rollback."""

    @abstractmethod
    async def save_checkpoint(
        self, state_dict: dict[str, object], metadata: CheckpointMetadata
    ) -> Path:
        """Safely write checkpoint file and update manifest."""
        raise NotImplementedError("NOT IMPLEMENTED: CheckpointManagerInterface.save_checkpoint")

    @abstractmethod
    async def load_best_checkpoint(self, experiment_dir: Path) -> CheckpointMetadata:
        """Locate and return best checkpoint according to validation criterion."""
        raise NotImplementedError(
            "NOT IMPLEMENTED: CheckpointManagerInterface.load_best_checkpoint"
        )
