import uuid
from datetime import datetime
from pydantic import BaseModel


class ProblemOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str

class AttemptOut(BaseModel):
    id: uuid.UUID
    problem_id: uuid.UUID
    status: str
    created_at: datetime

class StartAttemptIn(BaseModel):
    problem_id: uuid.UUID

class SubmitIn(BaseModel):
    text: str

class SubmitOut(BaseModel):
    submission_id: uuid.UUID
    evaluation_id: uuid.UUID
    evaluation_status: str

class CriterionAssessmentOut(BaseModel):
    criterion_name: str
    criterion_description: str
    score: str
    evidence: str
    concern: str | None
    suggestion: str | None
    confidence: str

class EvaluationOut(BaseModel):
    id: uuid.UUID
    status: str
    failure_reason: str | None
    assessments: list[CriterionAssessmentOut]

class ValidationErrorOut(BaseModel):
    issues: list[str]
