import json
import os

from anthropic import Anthropic

from domain.evaluation import CriterionAssessment, EvaluationResult
from domain.evaluator import Evaluator
from domain.rubric import Rubric

_VALID_SCORES = {"weak", "adequate", "strong"}
_VALID_CONFIDENCE = {"high", "medium", "low"}

_SYSTEM_PROMPT = """You are evaluating a learner's Low-Level Design (LLD) \
submission against a fixed rubric. You are not a general coding assistant \
here -- your only job is structured rubric assessment.

Rules:
- Assess EVERY criterion given, in the given order.
- Ground each assessment in the submission text: `evidence` must quote or \
closely paraphrase something the learner actually wrote, not a generic \
statement.
- There is more than one valid LLD solution. Do not penalize a design for \
differing from what you would have written, only for concrete, \
justifiable issues (missing responsibility, tight coupling, leaky \
abstraction, unaddressed requirement, etc).
- `score` must be exactly one of: "weak", "adequate", "strong".
- `confidence` must be exactly one of: "high", "medium", "low". Use "low" \
when the submission doesn't give you enough to assess that criterion \
well, rather than guessing.
- `concern` and `suggestion` may be null if genuinely not applicable, but \
prefer a concrete suggestion whenever score is not "strong".
- Output ONLY a JSON array, no prose before or after, no markdown fences. \
Each element must have exactly these keys: criterion_name, \
criterion_description, score, evidence, confidence, concern, suggestion.
"""


class LLMEvaluatorError(Exception):
    """Raised when the LLM call fails or returns something we can't parse
    into a valid EvaluationResult. The use case layer catches this and
    moves the Evaluation to FAILED -- it never propagates as a raw
    Anthropic SDK exception into application code."""


class LLMEvaluator(Evaluator):
    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None):
        self._model = model
        self._client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def evaluate(self, submission_text: str, rubric: Rubric) -> EvaluationResult:
        user_prompt = self._build_prompt(submission_text, rubric)
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:  # SDK errors: auth, rate limit, network, etc.
            raise LLMEvaluatorError(f"LLM call failed: {exc}") from exc

        raw_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return self._parse_result(raw_text, rubric)

    @staticmethod
    def _build_prompt(submission_text: str, rubric: Rubric) -> str:
        criteria_block = "\n".join(
            f"- {c.name}: {c.description}" for c in rubric.criteria
        )
        return (
            f"RUBRIC CRITERIA:\n{criteria_block}\n\n"
            f"SUBMISSION:\n{submission_text}\n\n"
            "Return the JSON array now."
        )

    @staticmethod
    def _parse_result(raw_text: str, rubric: Rubric) -> EvaluationResult:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            items = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMEvaluatorError(f"Model did not return valid JSON: {exc}") from exc

        expected_names = {c.name for c in rubric.criteria}
        assessments = []
        for item in items:
            try:
                name = item["criterion_name"]
                score = item["score"]
                confidence = item["confidence"]
            except KeyError as exc:
                raise LLMEvaluatorError(f"Assessment missing required key: {exc}") from exc

            if name not in expected_names:
                raise LLMEvaluatorError(f"Unknown criterion in model output: {name}")
            if score not in _VALID_SCORES:
                raise LLMEvaluatorError(f"Invalid score '{score}' for {name}")
            if confidence not in _VALID_CONFIDENCE:
                raise LLMEvaluatorError(f"Invalid confidence '{confidence}' for {name}")

            assessments.append(CriterionAssessment(
                criterion_name=name,
                criterion_description=item.get("criterion_description", ""),
                score=score,
                evidence=item.get("evidence", ""),
                confidence=confidence,
                concern=item.get("concern"),
                suggestion=item.get("suggestion"),
            ))

        missing = expected_names - {a.criterion_name for a in assessments}
        if missing:
            raise LLMEvaluatorError(f"Model omitted criteria: {missing}")

        return EvaluationResult(assessments=assessments)
