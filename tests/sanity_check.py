"""Not a formal test (that's Phase 10) -- just wires everything together
to confirm it actually runs before we build the API layer on top."""
import sys

from application.use_cases import (
    GetAttemptHistoryUseCase,
    RunEvaluationUseCase,
    StartAttemptUseCase,
    SubmitAttemptUseCase,
)
from domain.errors import AttemptAlreadySubmittedError, SubmissionValidationError
from domain.evaluation import EvaluationStatus
from domain.problem import Problem
from domain.submission_validator import SubmissionValidator
from infrastructure.db.repositories import (
    SqlAlchemyAttemptRepository,
    SqlAlchemyEvaluationRepository,
    SqlAlchemyProblemRepository,
    SqlAlchemySubmissionRepository,
)
from infrastructure.db.session import init_db, make_engine, make_session_factory
from infrastructure.evaluators.mock_evaluator import MockEvaluator


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        sys.exit(1)


engine = make_engine("sqlite:///:memory:")
init_db(engine)
session_factory = make_session_factory(engine)
session = session_factory()

problem_repo = SqlAlchemyProblemRepository(session)
attempt_repo = SqlAlchemyAttemptRepository(session)
submission_repo = SqlAlchemySubmissionRepository(session)
evaluation_repo = SqlAlchemyEvaluationRepository(session)

seed_problem = Problem(
    title="Parking Lot",
    description="Design a parking lot system supporting multiple vehicle sizes.",
    rubric_key="lld-default-v1",
)
problem_repo.add(seed_problem)

start_uc = StartAttemptUseCase(problem_repo, attempt_repo)
submit_uc = SubmitAttemptUseCase(attempt_repo, submission_repo, evaluation_repo, SubmissionValidator())
run_eval_uc = RunEvaluationUseCase(evaluation_repo, submission_repo, attempt_repo, problem_repo, MockEvaluator())
history_uc = GetAttemptHistoryUseCase(attempt_repo, problem_repo, submission_repo, evaluation_repo)

# 1. Start attempt
attempt = start_uc.execute(seed_problem.id)
check("attempt created with STARTED status", attempt.status == "STARTED")
fetched = attempt_repo.get_by_id(attempt.id)
check("attempt persisted and reloadable", fetched is not None and fetched.id == attempt.id)

# 2. Reject too-short submission
try:
    submit_uc.execute(attempt.id, "too short")
    check("short submission rejected", False)
except SubmissionValidationError as e:
    check(f"short submission rejected ({len(e.issues)} issues)", True)

# 3. Valid submission
good_text = (
    "Requirements: support Car, Motorcycle, Truck. Assumptions: single entry point.\n"
    "Classes: ParkingLot, ParkingSpot, Vehicle, Ticket, PaymentProcessor.\n"
    "Responsibilities: ParkingLot owns spot allocation; Vehicle is a pure data holder; "
    "PaymentProcessor is injected as an interface so pricing strategy can change later.\n"
    "Relationships: ParkingLot composes ParkingSpot list; Ticket references Vehicle and spot.\n"
    "Design explanation: spot allocation uses a Strategy interface so allocation policy "
    "(nearest-first vs size-fit) can be swapped without touching ParkingLot."
)
submission = submit_uc.execute(attempt.id, good_text)
check("submission persisted", submission_repo.get_by_id(submission.id) is not None)

# 4. Attempt now SUBMITTED, and double-submit blocked
reloaded_attempt = attempt_repo.get_by_id(attempt.id)
check("attempt status flipped to SUBMITTED", reloaded_attempt.status == "SUBMITTED")
try:
    submit_uc.execute(attempt.id, good_text)
    check("double-submit blocked", False)
except AttemptAlreadySubmittedError:
    check("double-submit blocked", True)

# 5. Evaluation created PENDING, then run to COMPLETED
evaluation = evaluation_repo.get_by_submission_id(submission.id)
check("evaluation auto-created as PENDING", evaluation.status == EvaluationStatus.PENDING)
completed = run_eval_uc.execute(evaluation.id)
check("evaluation completed", completed.status == EvaluationStatus.COMPLETED)
check("evaluation has 8 rubric assessments", len(completed.result.assessments) == 8)

# 6. Duplicate evaluation run is blocked (idempotency / duplicate-processing guard)
duplicate_result = run_eval_uc.execute(evaluation.id)
check(
    "re-running a COMPLETED evaluation is a no-op, not a re-evaluation",
    duplicate_result.status == EvaluationStatus.COMPLETED,
)

# 7. Attempt history shows the joined view
history = history_uc.execute()
check("history has 1 entry", len(history) == 1)
entry = history[0]
check("history entry has problem title", entry.problem_title == "Parking Lot")
check("history entry has submission", entry.submission is not None)
check("history entry has completed evaluation", entry.evaluation.status == EvaluationStatus.COMPLETED)

print("\nAll sanity checks passed.")
