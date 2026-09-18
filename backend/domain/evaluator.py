from abc import ABC, abstractmethod

from .evaluation import EvaluationResult
from .rubric import Rubric


class Evaluator(ABC):
    """Change Test B answer: today only LLMEvaluator exists; a future
    RuleBasedEvaluator or HumanEvaluator (a queue + UI for a human
    reviewer to enter assessments) implements this same interface and
    the practice flow (use case layer) does not change at all.

    Chosen as a class/interface rather than a plain function
    specifically because evaluators carry construction-time state
    (an API client, model name, config) -- a function would also be
    swappable in Python, but it has nowhere natural to hold that state
    without smuggling it in via closures or globals.
    """

    @abstractmethod
    def evaluate(self, submission_text: str, rubric: Rubric) -> EvaluationResult:
        """Given the evaluatable text and a fixed rubric, return a
        structured EvaluationResult. Implementations only ever receive
        judgment-based questions (responsibilities, coupling, trade-offs)
        -- deterministic checks are SubmissionValidator's job and run
        before an Evaluator is ever invoked (decision 18)."""
        raise NotImplementedError
