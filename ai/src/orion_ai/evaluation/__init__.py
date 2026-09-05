"""Evaluation subsystem package."""

from orion_ai.evaluation.configs import EvaluationConfig
from orion_ai.evaluation.interfaces import EvaluatorInterface
from orion_ai.evaluation.registry import EvaluatorRegistry
from orion_ai.evaluation.schemas import (
    BenchmarkSummary,
    ConfusionMatrixData,
    MetricResult,
)

__all__ = [
    "BenchmarkSummary",
    "ConfusionMatrixData",
    "EvaluationConfig",
    "EvaluatorInterface",
    "EvaluatorRegistry",
    "MetricResult",
]
