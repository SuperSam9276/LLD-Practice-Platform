import uuid
from datetime import datetime, timezone

from .rubric import Rubric, get_rubric


class Problem:
    """An LLD practice problem (Parking Lot, Vending Machine, Elevator).
    Owns its own Rubric reference (decision 22) -- not a global
    singleton -- even though the MVP has all three problems sharing one
    Rubric instance. Small extensibility hook for per-problem rubrics
    later without a schema change (rubric_key value just changes)."""

    def __init__(
        self,
        title: str,
        description: str,
        rubric_key: str,
        id: uuid.UUID | None = None,
        created_at: datetime | None = None,
    ):
        self.id = id or uuid.uuid4()
        self.title = title
        self.description = description
        self.rubric_key = rubric_key
        self.created_at = created_at or datetime.now(timezone.utc)

    @property
    def rubric(self) -> Rubric:
        return get_rubric(self.rubric_key)
