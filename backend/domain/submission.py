import uuid
from datetime import datetime, timezone

from .submission_content import SubmissionContent


class Submission:
    """The learner's actual design content. Effectively immutable once
    created -- reason to change is content/format concerns only
    (Change Test A pressure point). No status of its own; lifecycle
    tracking belongs to Evaluation, not here (decision 14)."""

    def __init__(
        self,
        attempt_id: uuid.UUID,
        content: SubmissionContent,
        id: uuid.UUID | None = None,
        created_at: datetime | None = None,
    ):
        self.id = id or uuid.uuid4()
        self.attempt_id = attempt_id
        self.content = content
        self.created_at = created_at or datetime.now(timezone.utc)
