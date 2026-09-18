import uuid
from datetime import datetime, timezone

from .errors import AttemptAlreadySubmittedError


class AttemptStatus:
    STARTED = "STARTED"
    SUBMITTED = "SUBMITTED"


class Attempt:
    """One practice session on a Problem. Reason to change: session /
    practice-tracking concerns (decision 14). Cardinality: 1 Attempt
    -> 0..1 Submission, expressed here as a status flag rather than a
    held reference, to avoid a circular Attempt<->Submission dependency.
    """

    def __init__(
        self,
        problem_id: uuid.UUID,
        id: uuid.UUID | None = None,
        status: str = AttemptStatus.STARTED,
        created_at: datetime | None = None,
    ):
        self.id = id or uuid.uuid4()
        self.problem_id = problem_id
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    def mark_submitted(self) -> None:
        """Domain-side guard mirroring the DB's UNIQUE(attempt_id) on
        submissions (decision 5.4/32). Raises if this attempt already
        has a submission, so the use case gets a meaningful domain
        error instead of a raw IntegrityError."""
        if self.status == AttemptStatus.SUBMITTED:
            raise AttemptAlreadySubmittedError(
                f"Attempt {self.id} already has a submission"
            )
        self.status = AttemptStatus.SUBMITTED

    def is_submitted(self) -> bool:
        return self.status == AttemptStatus.SUBMITTED
