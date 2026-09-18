import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .errors import InvalidEvaluationTransitionError


class EvaluationStatus:
    PENDING = "PENDING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Legal transitions. This is the ONLY place transition rules live --
# deliberately not a DB trigger (decision 5.4): the DB's CHECK
# constraint on evaluations.status only blocks garbage values, it
# cannot express "not from COMPLETED backward to EVALUATING" because
# that requires comparing old-row to new-row, which is business
# meaning, not a structural fact.
_ALLOWED_TRANSITIONS = {
    EvaluationStatus.PENDING: {EvaluationStatus.EVALUATING},
    EvaluationStatus.EVALUATING: {EvaluationStatus.COMPLETED, EvaluationStatus.FAILED},
    EvaluationStatus.COMPLETED: set(),
    EvaluationStatus.FAILED: set(),
}


@dataclass(frozen=True)
class CriterionAssessment:
    """One rubric criterion's assessment. criterion_name/description are
    COPIED values, not a live reference to a RubricCriterion (decision
    5.3) -- this row is a receipt of what was evaluated at this moment,
    and must not silently reword itself if the rubric changes later."""
    criterion_name: str
    criterion_description: str
    score: str  # 'weak' | 'adequate' | 'strong'
    evidence: str
    confidence: str  # 'high' | 'medium' | 'low'
    concern: str | None = None
    suggestion: str | None = None


@dataclass(frozen=True)
class EvaluationResult:
    assessments: list[CriterionAssessment] = field(default_factory=list)


class Evaluation:
    """Owns the PENDING -> EVALUATING -> COMPLETED/FAILED lifecycle.
    Cardinality: 1 Submission -> 1 Evaluation. Reason to change:
    evaluation process / rubric / evaluator-swapping concerns (Change
    Test B pressure point)."""

    def __init__(
        self,
        submission_id: uuid.UUID,
        id: uuid.UUID | None = None,
        status: str = EvaluationStatus.PENDING,
        result: EvaluationResult | None = None,
        failure_reason: str | None = None,
        created_at: datetime | None = None,
        completed_at: datetime | None = None,
    ):
        self.id = id or uuid.uuid4()
        self.submission_id = submission_id
        self.status = status
        self.result = result
        self.failure_reason = failure_reason
        self.created_at = created_at or datetime.now(timezone.utc)
        self.completed_at = completed_at

    def _transition_to(self, new_status: str) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidEvaluationTransitionError(
                f"Cannot move Evaluation {self.id} from {self.status} to {new_status}"
            )
        self.status = new_status

    def start(self) -> None:
        self._transition_to(EvaluationStatus.EVALUATING)

    def complete(self, result: EvaluationResult) -> None:
        self._transition_to(EvaluationStatus.COMPLETED)
        self.result = result
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, reason: str) -> None:
        self._transition_to(EvaluationStatus.FAILED)
        self.failure_reason = reason
        self.completed_at = datetime.now(timezone.utc)
