"""Concrete repositories. Each takes a SQLAlchemy Session at construction
and commits its own writes.

Decision flagged, not hidden: this means each repository call is its own
transaction (no cross-repository atomicity -- e.g. SubmitAttemptUseCase's
attempt-update and submission-insert are two separate commits, not one).
A Unit-of-Work object (one Session, one commit, shared across repos in a
use case) would fix that, at the cost of another abstraction layer. For
this MVP's failure modes (a crash between two commits leaves an Attempt
marked SUBMITTED with no Submission row -- recoverable by re-querying,
not data-corrupting) this is an acceptable, explicitly-noted trade-off
rather than an oversight. Worth revisiting first if this became a real
product.
"""
import json
import uuid

from sqlalchemy.orm import Session

from application.ports import (
    AttemptRepository,
    EvaluationRepository,
    ProblemRepository,
    SubmissionRepository,
)
from domain.attempt import Attempt
from domain.evaluation import CriterionAssessment, Evaluation, EvaluationResult
from domain.problem import Problem
from domain.submission import Submission
from domain.submission_content import SubmissionContent, TextSubmissionContent
from infrastructure.db.models import (
    AttemptModel,
    EvaluationModel,
    ProblemModel,
    SubmissionModel,
)


def _build_content(content_type: str, raw_text: str) -> SubmissionContent:
    """Reverse of SubmissionContent.content_type. Only TEXT exists today;
    a future 'DIAGRAM' branch is the one place that needs to grow for
    Change Test A -- nothing else in this file does."""
    if content_type == "TEXT":
        return TextSubmissionContent(raw_text)
    raise ValueError(f"Unknown submission content_type: {content_type}")


class SqlAlchemyProblemRepository(ProblemRepository):
    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, problem_id: uuid.UUID) -> Problem | None:
        row = self._session.get(ProblemModel, str(problem_id))
        return self._to_domain(row) if row else None

    def list_all(self) -> list[Problem]:
        rows = self._session.query(ProblemModel).order_by(ProblemModel.created_at).all()
        return [self._to_domain(r) for r in rows]

    def add(self, problem: Problem) -> None:
        """Not part of ProblemRepository's ABC (problems are seed data,
        not user-created in the MVP) -- exposed here only for the seed
        script to use, via this concrete class, not the interface."""
        row = ProblemModel(
            id=str(problem.id),
            title=problem.title,
            description=problem.description,
            rubric_key=problem.rubric_key,
            created_at=problem.created_at,
        )
        self._session.add(row)
        self._session.commit()

    @staticmethod
    def _to_domain(row: ProblemModel) -> Problem:
        return Problem(
            id=uuid.UUID(row.id),
            title=row.title,
            description=row.description,
            rubric_key=row.rubric_key,
            created_at=row.created_at,
        )


class SqlAlchemyAttemptRepository(AttemptRepository):
    def __init__(self, session: Session):
        self._session = session

    def add(self, attempt: Attempt) -> None:
        row = AttemptModel(
            id=str(attempt.id),
            problem_id=str(attempt.problem_id),
            status=attempt.status,
            created_at=attempt.created_at,
        )
        self._session.add(row)
        self._session.commit()

    def get_by_id(self, attempt_id: uuid.UUID) -> Attempt | None:
        row = self._session.get(AttemptModel, str(attempt_id))
        return self._to_domain(row) if row else None

    def update(self, attempt: Attempt) -> None:
        row = self._session.get(AttemptModel, str(attempt.id))
        if row is None:
            raise ValueError(f"Attempt {attempt.id} not found")
        row.status = attempt.status
        self._session.commit()

    def list_all(self) -> list[Attempt]:
        rows = (
            self._session.query(AttemptModel)
            .order_by(AttemptModel.created_at.desc())
            .all()
        )
        return [self._to_domain(r) for r in rows]

    @staticmethod
    def _to_domain(row: AttemptModel) -> Attempt:
        return Attempt(
            id=uuid.UUID(row.id),
            problem_id=uuid.UUID(row.problem_id),
            status=row.status,
            created_at=row.created_at,
        )


class SqlAlchemySubmissionRepository(SubmissionRepository):
    def __init__(self, session: Session):
        self._session = session

    def add(self, submission: Submission) -> None:
        row = SubmissionModel(
            id=str(submission.id),
            attempt_id=str(submission.attempt_id),
            content_type=submission.content.content_type,
            raw_text=submission.content.get_evaluatable_text(),
            created_at=submission.created_at,
        )
        self._session.add(row)
        self._session.commit()

    def get_by_id(self, submission_id: uuid.UUID) -> Submission | None:
        row = self._session.get(SubmissionModel, str(submission_id))
        return self._to_domain(row) if row else None

    def get_by_attempt_id(self, attempt_id: uuid.UUID) -> Submission | None:
        row = (
            self._session.query(SubmissionModel)
            .filter_by(attempt_id=str(attempt_id))
            .one_or_none()
        )
        return self._to_domain(row) if row else None

    @staticmethod
    def _to_domain(row: SubmissionModel) -> Submission:
        return Submission(
            id=uuid.UUID(row.id),
            attempt_id=uuid.UUID(row.attempt_id),
            content=_build_content(row.content_type, row.raw_text),
            created_at=row.created_at,
        )


class SqlAlchemyEvaluationRepository(EvaluationRepository):
    def __init__(self, session: Session):
        self._session = session

    def add(self, evaluation: Evaluation) -> None:
        row = EvaluationModel(
            id=str(evaluation.id),
            submission_id=str(evaluation.submission_id),
            status=evaluation.status,
            result_json=self._result_to_json(evaluation.result),
            failure_reason=evaluation.failure_reason,
            created_at=evaluation.created_at,
            completed_at=evaluation.completed_at,
        )
        self._session.add(row)
        self._session.commit()

    def update(self, evaluation: Evaluation) -> None:
        row = self._session.get(EvaluationModel, str(evaluation.id))
        if row is None:
            raise ValueError(f"Evaluation {evaluation.id} not found")
        row.status = evaluation.status
        row.result_json = self._result_to_json(evaluation.result)
        row.failure_reason = evaluation.failure_reason
        row.completed_at = evaluation.completed_at
        self._session.commit()

    def get_by_id(self, evaluation_id: uuid.UUID) -> Evaluation | None:
        row = self._session.get(EvaluationModel, str(evaluation_id))
        return self._to_domain(row) if row else None

    def get_by_submission_id(self, submission_id: uuid.UUID) -> Evaluation | None:
        row = (
            self._session.query(EvaluationModel)
            .filter_by(submission_id=str(submission_id))
            .one_or_none()
        )
        return self._to_domain(row) if row else None

    @staticmethod
    def _result_to_json(result: EvaluationResult | None) -> str | None:
        if result is None:
            return None
        return json.dumps([
            {
                "criterion_name": a.criterion_name,
                "criterion_description": a.criterion_description,
                "score": a.score,
                "evidence": a.evidence,
                "confidence": a.confidence,
                "concern": a.concern,
                "suggestion": a.suggestion,
            }
            for a in result.assessments
        ])

    @staticmethod
    def _result_from_json(raw: str | None) -> EvaluationResult | None:
        if raw is None:
            return None
        items = json.loads(raw)
        return EvaluationResult(
            assessments=[CriterionAssessment(**item) for item in items]
        )

    @classmethod
    def _to_domain(cls, row: EvaluationModel) -> Evaluation:
        return Evaluation(
            id=uuid.UUID(row.id),
            submission_id=uuid.UUID(row.submission_id),
            status=row.status,
            result=cls._result_from_json(row.result_json),
            failure_reason=row.failure_reason,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )
