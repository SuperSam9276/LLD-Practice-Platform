class DomainError(Exception):
    """Base class for all domain-level errors."""


class AttemptAlreadySubmittedError(DomainError):
    """Raised when trying to submit on an Attempt that already has a Submission."""


class InvalidEvaluationTransitionError(DomainError):
    """Raised when an Evaluation tries to move to a status not reachable
    from its current status."""


class SubmissionValidationError(DomainError):
    """Raised when a submission fails deterministic validation.
    Carries the list of human-readable issues found."""

    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__(f"Submission invalid: {issues}")
