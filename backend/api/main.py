"""Thin API layer: routes call use cases, nothing else. Background-task
evaluation per decision 37 -- submit endpoint returns immediately;
evaluation runs after response, in its own DB session (never the
request-scoped one, which closes when the response is sent)."""
import uuid

from fastapi import FastAPI, BackgroundTasks, HTTPException

from domain.submission_validator import SubmissionValidator
from domain.errors import SubmissionValidationError, AttemptAlreadySubmittedError

from application.use_cases import (
    ListProblemsUseCase, GetProblemUseCase, StartAttemptUseCase,
    SubmitAttemptUseCase, RunEvaluationUseCase, GetEvaluationUseCase,
    GetAttemptHistoryUseCase,
)
from infrastructure.db.repositories import (
    SqlAlchemyProblemRepository, SqlAlchemyAttemptRepository,
    SqlAlchemySubmissionRepository, SqlAlchemyEvaluationRepository,
)

from .db import SessionLocal, get_evaluator
from .schemas import (
    ProblemOut, AttemptOut, StartAttemptIn, SubmitIn, SubmitOut,
    EvaluationOut, CriterionAssessmentOut,
)

app = FastAPI(title="LLD Practice Platform API")


def _run_evaluation_background(evaluation_id: uuid.UUID) -> None:
    """Opens its OWN session -- decision 37's key gotcha."""
    session = SessionLocal()
    try:
        use_case = RunEvaluationUseCase(
            evaluations=SqlAlchemyEvaluationRepository(session),
            submissions=SqlAlchemySubmissionRepository(session),
            problems=SqlAlchemyProblemRepository(session),
            attempts=SqlAlchemyAttemptRepository(session),
            evaluator=get_evaluator(),
        )
        use_case.execute(evaluation_id)
    finally:
        session.close()


@app.get("/problems", response_model=list[ProblemOut])
def list_problems():
    session = SessionLocal()
    try:
        problems = ListProblemsUseCase(SqlAlchemyProblemRepository(session)).execute()
        return [ProblemOut(id=p.id, title=p.title, description=p.description) for p in problems]
    finally:
        session.close()


@app.get("/problems/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: uuid.UUID):
    session = SessionLocal()
    try:
        p = GetProblemUseCase(SqlAlchemyProblemRepository(session)).execute(problem_id)
        if p is None:
            raise HTTPException(404, "Problem not found")
        return ProblemOut(id=p.id, title=p.title, description=p.description)
    finally:
        session.close()


@app.post("/attempts", response_model=AttemptOut)
def start_attempt(body: StartAttemptIn):
    session = SessionLocal()
    try:
        use_case = StartAttemptUseCase(
            problems=SqlAlchemyProblemRepository(session),
            attempts=SqlAlchemyAttemptRepository(session),
        )
        try:
            attempt = use_case.execute(body.problem_id)
        except ValueError as e:
            raise HTTPException(404, str(e))
        return AttemptOut(id=attempt.id, problem_id=attempt.problem_id,
                           status=attempt.status, created_at=attempt.created_at)
    finally:
        session.close()


@app.post("/attempts/{attempt_id}/submit", response_model=SubmitOut)
def submit_attempt(attempt_id: uuid.UUID, body: SubmitIn, background_tasks: BackgroundTasks):
    session = SessionLocal()
    try:
        use_case = SubmitAttemptUseCase(
            attempts=SqlAlchemyAttemptRepository(session),
            submissions=SqlAlchemySubmissionRepository(session),
            evaluations=SqlAlchemyEvaluationRepository(session),
            validator=SubmissionValidator(),
        )
        try:
            submission, evaluation = use_case.execute(attempt_id, body.text)
        except SubmissionValidationError as e:
            raise HTTPException(422, detail={"issues": e.issues})
        except AttemptAlreadySubmittedError as e:
            raise HTTPException(409, str(e))
        except ValueError as e:
            raise HTTPException(404, str(e))

        background_tasks.add_task(_run_evaluation_background, evaluation.id)

        return SubmitOut(
            submission_id=submission.id, evaluation_id=evaluation.id,
            evaluation_status=evaluation.status,
        )
    finally:
        session.close()


@app.get("/evaluations/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(evaluation_id: uuid.UUID):
    session = SessionLocal()
    try:
        e = GetEvaluationUseCase(SqlAlchemyEvaluationRepository(session)).execute(evaluation_id)
        if e is None:
            raise HTTPException(404, "Evaluation not found")
        assessments = []
        if e.result:
            assessments = [
                CriterionAssessmentOut(
                    criterion_name=a.criterion_name, criterion_description=a.criterion_description,
                    score=a.score, evidence=a.evidence, concern=a.concern,
                    suggestion=a.suggestion, confidence=a.confidence,
                ) for a in e.result.assessments
            ]
        return EvaluationOut(id=e.id, status=e.status, failure_reason=e.failure_reason,
                              assessments=assessments)
    finally:
        session.close()


@app.get("/attempts", response_model=list[AttemptOut])
def list_attempts():
    session = SessionLocal()
    try:
        attempts = GetAttemptHistoryUseCase(SqlAlchemyAttemptRepository(session)).execute()
        return [AttemptOut(id=a.id, problem_id=a.problem_id, status=a.status,
                            created_at=a.created_at) for a in attempts]
    finally:
        session.close()
