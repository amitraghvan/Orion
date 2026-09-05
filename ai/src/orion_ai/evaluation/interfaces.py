"""Model evaluator interface."""

from abc import ABC, abstractmethod
from typing import Any

from orion_ai.evaluation.schemas import BenchmarkSummary


class EvaluatorInterface(ABC):
    """Interface for running standardized model evaluation against validation datasets."""

    @abstractmethod
    async def evaluate_dataset(self, model: Any, dataloader: Any) -> BenchmarkSummary:
        """Compute metrics, confusion matrices, and inference latency statistics."""
        raise NotImplementedError("NOT IMPLEMENTED: EvaluatorInterface.evaluate_dataset")
