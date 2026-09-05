"""Evaluator registry."""

from orion_ai.evaluation.interfaces import EvaluatorInterface


class EvaluatorRegistry:
    """Registry mapping task domains to specialized evaluator implementations."""

    _evaluators: dict[str, type[EvaluatorInterface]] = {}

    @classmethod
    def register(cls, task_domain: str, evaluator_cls: type[EvaluatorInterface]) -> None:
        cls._evaluators[task_domain] = evaluator_cls

    @classmethod
    def get(cls, task_domain: str) -> type[EvaluatorInterface]:
        if task_domain not in cls._evaluators:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Evaluator for domain {task_domain} is not registered."
            )
        return cls._evaluators[task_domain]
