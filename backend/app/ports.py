"""Repository interfaces (ports). Use cases depend on these, never on
SQLAlchemy directly. Kept as ABCs, matching the style already used for
Evaluator/SubmissionContent in the domain layer, for consistency
rather than because ABC beats Protocol on merits (decision: consistency
over cleverness).

Each method signature works entirely in domain objects (Problem,
Attempt, Submission, Evaluation) -- never ORM rows, never dicts. That
boundary is what lets the application layer stay framework-agnostic.
"""
import uuid
from abc import ABC, abstractmethod

from domain.attempt import Attempt
from domain.evaluation import Evaluation
from domain.problem import Problem
from domain.submission import Submission


class ProblemRepository(ABC):
    @abstractmethod
    def get_by_id(self, problem_id: uuid.UUID) -> Problem | None: ...

    @abstractmethod
    def list_all(self) -> list[Problem]: ...


class AttemptRepository(ABC):
    @abstractmethod
    def add(self, attempt: Attempt) -> None: ...

    @abstractmethod
    def get_by_id(self, attempt_id: uuid.UUID) -> Attempt | None: ...

    @abstractmethod
    def update(self, attempt: Attempt) -> None: ...

    @abstractmethod
    def list_all(self) -> list[Attempt]:
        """Newest first. Backs attempt history."""
        ...


class SubmissionRepository(ABC):
    @abstractmethod
    def add(self, submission: Submission) -> None: ...

    @abstractmethod
    def get_by_id(self, submission_id: uuid.UUID) -> Submission | None: ...

    @abstractmethod
    def get_by_attempt_id(self, attempt_id: uuid.UUID) -> Submission | None: ...


class EvaluationRepository(ABC):
    @abstractmethod
    def add(self, evaluation: Evaluation) -> None: ...

    @abstractmethod
    def update(self, evaluation: Evaluation) -> None: ...

    @abstractmethod
    def get_by_id(self, evaluation_id: uuid.UUID) -> Evaluation | None: ...

    @abstractmethod
    def get_by_submission_id(self, submission_id: uuid.UUID) -> Evaluation | None: ...
