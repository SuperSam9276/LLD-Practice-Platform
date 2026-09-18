import sys
sys.path.insert(0, "/home/claude/lld_platform")

from domain.problem import Problem
from domain.submission_validator import SubmissionValidator
from domain.errors import SubmissionValidationError, AttemptAlreadySubmittedError

from application.ports import ProblemRepository, AttemptRepository, SubmissionRepository, EvaluationRepository
from application.use_cases import (
    ListProblemsUseCase, StartAttemptUseCase, SubmitAttemptUseCase,
    RunEvaluationUseCase, GetAttemptHistoryUseCase,
)
from infrastructure.evaluators.mock_evaluator import MockEvaluator


class InMemoryProblemRepo(ProblemRepository):
    def __init__(self, problems): self._d = {p.id: p for p in problems}
    def get(self, pid): return self._d.get(pid)
    def list_all(self): return list(self._d.values())

class InMemoryAttemptRepo(AttemptRepository):
    def __init__(self): self._d = {}
    def add(self, a): self._d[a.id] = a
    def get(self, aid): return self._d.get(aid)
    def update(self, a): self._d[a.id] = a
    def list_all(self): return sorted(self._d.values(), key=lambda a: a.created_at, reverse=True)

class InMemorySubmissionRepo(SubmissionRepository):
    def __init__(self): self._d = {}
    def add(self, s): self._d[s.id] = s
    def get_by_attempt(self, aid):
        return next((s for s in self._d.values() if s.attempt_id == aid), None)
    def get(self, sid): return self._d.get(sid)

class InMemoryEvaluationRepo(EvaluationRepository):
    def __init__(self): self._d = {}
    def add(self, e): self._d[e.id] = e
    def update(self, e): self._d[e.id] = e
    def get(self, eid): return self._d.get(eid)
    def get_by_submission(self, sid):
        return next((e for e in self._d.values() if e.submission_id == sid), None)


problem = Problem(title="Parking Lot", description="Design a parking lot system.",
                   rubric_key="lld-default-v1")
problems_repo = InMemoryProblemRepo([problem])
attempts_repo = InMemoryAttemptRepo()
submissions_repo = InMemorySubmissionRepo()
evaluations_repo = InMemoryEvaluationRepo()
evaluator = MockEvaluator()

# 1. list problems
listed = ListProblemsUseCase(problems_repo).execute()
assert len(listed) == 1
print("OK: list problems")

# 2. start attempt
attempt = StartAttemptUseCase(problems_repo, attempts_repo).execute(problem.id)
assert attempt.status == "STARTED"
print("OK: start attempt")

# 3. submit (valid)
submit_uc = SubmitAttemptUseCase(attempts_repo, submissions_repo, evaluations_repo, SubmissionValidator())
submission, evaluation = submit_uc.execute(
    attempt.id, "The ParkingLot class has responsibility for spot allocation, and interacts with Vehicle and ParkingSpot classes." * 2
)
assert evaluation.status == "PENDING"
print("OK: submit valid -> PENDING evaluation")

# 3b. double-submit blocked
try:
    submit_uc.execute(attempt.id, "second submission text with enough length and class responsibility words" * 2)
    assert False
except AttemptAlreadySubmittedError:
    print("OK: double-submit blocked")

# 3c. invalid submission rejected on a fresh attempt
attempt2 = StartAttemptUseCase(problems_repo, attempts_repo).execute(problem.id)
try:
    submit_uc.execute(attempt2.id, "too short")
    assert False
except SubmissionValidationError as e:
    assert len(e.issues) > 0
    print("OK: invalid submission rejected:", e.issues)

# 4. run evaluation (mock)
run_uc = RunEvaluationUseCase(evaluations_repo, submissions_repo, problems_repo, attempts_repo, evaluator)
completed = run_uc.execute(evaluation.id)
assert completed.status == "COMPLETED"
assert len(completed.result.assessments) == 8  # 8 rubric criteria
print("OK: evaluation completed with", len(completed.result.assessments), "assessments")

# 4b. idempotent re-run
completed_again = run_uc.execute(evaluation.id)
assert completed_again.status == "COMPLETED"
print("OK: idempotent re-run is a no-op")

# 5. history
history = GetAttemptHistoryUseCase(attempts_repo).execute()
assert len(history) == 2
print("OK: history has", len(history), "attempts")

print("\nALL USE-CASE LAYER SANITY CHECKS PASSED")
