"""Use cases (application services). Each one is a single learner-facing
action from the journey: Choose problem -> Think/design -> Submit -> Get
feedback -> Review -> Try again.

Rule followed throughout: a use case ORCHESTRATES (calls domain methods,
calls repositories, calls the evaluator) -- it does not itself decide
business rules. E.g. "can this attempt be submitted?" is
Attempt.mark_submitted()'s job, not SubmitAttemptUseCase's; the use case
just calls it and lets the exception propagate. This is what keeps
Change Test A/B possible: swap a repository or the evaluator, and no
use case body changes.
"""
import uuid
from dataclasses import dataclass

from application.ports import (
    AttemptRepository,
    EvaluationRepository,
    ProblemRepository,
    SubmissionRepository,
)
from domain.attempt import Attempt
from domain.errors import DomainError
from domain.evaluation import Evaluation, EvaluationStatus
from domain.evaluator import Evaluator
from domain.submission import Submission
from domain.submission_content import TextSubmissionContent
from domain.submission_validator import SubmissionValidator


class ProblemNotFoundError(DomainError):
    pass


class AttemptNotFoundError(DomainError):
    pass


class SubmissionNotFoundError(DomainError):
    pass


class EvaluationNotFoundError(DomainError):
    pass


class StartAttemptUseCase:
    def __init__(self, problem_repo: ProblemRepository, attempt_repo: AttemptRepository):
        self._problems = problem_repo
        self._attempts = attempt_repo

    def execute(self, problem_id: uuid.UUID) -> Attempt:
        problem = self._problems.get_by_id(problem_id)
        if problem is None:
            raise ProblemNotFoundError(f"Problem {problem_id} not found")
        attempt = Attempt(problem_id=problem.id)
        self._attempts.add(attempt)
        return attempt


class SubmitAttemptUseCase:
    """Deliberately synchronous and evaluation-free: it stores the
    Submission and creates a PENDING Evaluation, then returns. Running
    the evaluation is a separate use case (RunEvaluationUseCase),
    triggered right after in the API layer (e.g. FastAPI BackgroundTasks)
    -- but the two are decoupled here so a slow/failing evaluator can
    never cause a lost submission (decision from PROJECT_STATE: 'store
    submission before evaluation begins')."""

    def __init__(
        self,
        attempt_repo: AttemptRepository,
        submission_repo: SubmissionRepository,
        evaluation_repo: EvaluationRepository,
        validator: SubmissionValidator,
    ):
        self._attempts = attempt_repo
        self._submissions = submission_repo
        self._evaluations = evaluation_repo
        self._validator = validator

    def execute(self, attempt_id: uuid.UUID, raw_text: str) -> Submission:
        attempt = self._attempts.get_by_id(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"Attempt {attempt_id} not found")

        content = TextSubmissionContent(raw_text)

        # Deterministic checks first -- cheap, no external dependency,
        # and gate everything downstream (decision 18/32).
        issues = self._validator.validate(content)
        if issues:
            from domain.errors import SubmissionValidationError
            raise SubmissionValidationError(issues)

        # Domain guard: raises AttemptAlreadySubmittedError if this
        # attempt already has a submission. Checked AFTER validation so
        # a bad resubmission attempt gets the more specific error first
        # -- an arbitrary but reasonable ordering choice, not a hard rule.
        attempt.mark_submitted()

        submission = Submission(attempt_id=attempt.id, content=content)
        self._submissions.add(submission)
        self._attempts.update(attempt)

        evaluation = Evaluation(submission_id=submission.id)
        self._evaluations.add(evaluation)

        return submission


class RunEvaluationUseCase:
    """Advances one Evaluation from PENDING through EVALUATING to
    COMPLETED or FAILED. Idempotent by construction: if called twice on
    an already-EVALUATING or already-terminal Evaluation, `start()`
    raises InvalidEvaluationTransitionError rather than double-running
    the evaluator -- this IS the duplicate-processing guard the
    assignment asks for, reusing the state machine instead of adding a
    separate lock/flag."""

    def __init__(
        self,
        evaluation_repo: EvaluationRepository,
        submission_repo: SubmissionRepository,
        attempt_repo: AttemptRepository,
        problem_repo: ProblemRepository,
        evaluator: Evaluator,
    ):
        self._evaluations = evaluation_repo
        self._submissions = submission_repo
        self._attempts = attempt_repo
        self._problems = problem_repo
        self._evaluator = evaluator

    def execute(self, evaluation_id: uuid.UUID) -> Evaluation:
        evaluation = self._evaluations.get_by_id(evaluation_id)
        if evaluation is None:
            raise EvaluationNotFoundError(f"Evaluation {evaluation_id} not found")

        if evaluation.status != EvaluationStatus.PENDING:
            # Duplicate-processing guard: a retried request (double-click,
            # background-task retry, etc.) that targets an evaluation
            # already EVALUATING/COMPLETED/FAILED is a no-op, not an
            # error. We deliberately catch this here rather than let
            # InvalidEvaluationTransitionError propagate -- that error
            # exists to protect Evaluation's invariant, not to be the
            # public API for "is this a duplicate call?". Callers of
            # this use case shouldn't need to know the state machine's
            # exception type just to be safely idempotent.
            return evaluation

        evaluation.start()
        self._evaluations.update(evaluation)

        submission = self._submissions.get_by_id(evaluation.submission_id)
        if submission is None:
            raise SubmissionNotFoundError(f"Submission {evaluation.submission_id} not found")

        attempt = self._attempts.get_by_id(submission.attempt_id)
        problem = self._problems.get_by_id(attempt.problem_id)
        rubric = problem.rubric

        try:
            result = self._evaluator.evaluate(
                submission.content.get_evaluatable_text(), rubric
            )
        except Exception as exc:
            evaluation.fail(str(exc))
            self._evaluations.update(evaluation)
            return evaluation

        evaluation.complete(result)
        self._evaluations.update(evaluation)
        return evaluation


@dataclass(frozen=True)
class AttemptHistoryEntry:
    """Read-model DTO for the history view -- deliberately NOT a domain
    object. It's a join of Attempt + Problem + Submission + Evaluation
    shaped for one screen; giving it its own type keeps that shaping out
    of the domain classes, which have no reason to know about each
    other's display needs."""
    attempt: Attempt
    problem_title: str
    submission: Submission | None
    evaluation: Evaluation | None


class GetAttemptHistoryUseCase:
    def __init__(
        self,
        attempt_repo: AttemptRepository,
        problem_repo: ProblemRepository,
        submission_repo: SubmissionRepository,
        evaluation_repo: EvaluationRepository,
    ):
        self._attempts = attempt_repo
        self._problems = problem_repo
        self._submissions = submission_repo
        self._evaluations = evaluation_repo

    def execute(self) -> list[AttemptHistoryEntry]:
        entries = []
        for attempt in self._attempts.list_all():
            problem = self._problems.get_by_id(attempt.problem_id)
            submission = self._submissions.get_by_attempt_id(attempt.id)
            evaluation = (
                self._evaluations.get_by_submission_id(submission.id)
                if submission else None
            )
            entries.append(AttemptHistoryEntry(
                attempt=attempt,
                problem_title=problem.title if problem else "Unknown problem",
                submission=submission,
                evaluation=evaluation,
            ))
        return entries
