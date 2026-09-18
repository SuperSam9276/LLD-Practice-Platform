"""SQLAlchemy ORM models. These are NOT the domain objects (decision:
keep domain classes framework-free). Repositories map between the two.

UUIDs are stored as 36-char strings rather than a native UUID column
type -- SQLite has no UUID type, and Postgres's UUID type would make
this schema non-portable between the two for no MVP benefit.
"""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProblemModel(Base):
    __tablename__ = "problems"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    rubric_key: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=_now)


class AttemptModel(Base):
    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    problem_id: Mapped[str] = mapped_column(ForeignKey("problems.id"))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(default=_now)

    __table_args__ = (
        CheckConstraint("status IN ('STARTED','SUBMITTED')", name="ck_attempt_status"),
    )


class SubmissionModel(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # UNIQUE enforces "0..1 Submission per Attempt" at the DB level too --
    # the domain guard (Attempt.mark_submitted) is the primary defense,
    # this is the backstop against races / bugs that bypass the domain layer.
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), unique=True)
    content_type: Mapped[str] = mapped_column(String(20))
    raw_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class EvaluationModel(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20))
    # Stored as JSON text, not normalized into a criterion_assessments
    # table. MVP reason: the result is always read/written whole (as one
    # EvaluationResult), never queried by individual criterion, so a
    # join buys nothing and costs a mapper layer.
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','EVALUATING','COMPLETED','FAILED')",
            name="ck_evaluation_status",
        ),
    )
