from domain.evaluation import CriterionAssessment, EvaluationResult
from domain.evaluator import Evaluator
from domain.rubric import Rubric


class MockEvaluator(Evaluator):
    """Deterministic stand-in for LLMEvaluator. Exists for two reasons:
    (1) tests must not depend on network/API-key availability, (2) it's
    the fallback the demo can run on if there's no API key handy during
    review. It implements the SAME Evaluator interface as LLMEvaluator --
    this is Change Test B in miniature: the use case layer that calls
    `evaluator.evaluate(...)` cannot tell which one it's holding.
    """

    def evaluate(self, submission_text: str, rubric: Rubric) -> EvaluationResult:
        assessments = [
            CriterionAssessment(
                criterion_name=c.name,
                criterion_description=c.description,
                score="adequate",
                evidence=(
                    "Mock evaluation: submission text is "
                    f"{len(submission_text)} characters long."
                ),
                confidence="low",
                concern="This is a mock result; no real judgment was performed.",
                suggestion="Configure ANTHROPIC_API_KEY to use LLMEvaluator for real feedback.",
            )
            for c in rubric.criteria
        ]
        return EvaluationResult(assessments=assessments)
