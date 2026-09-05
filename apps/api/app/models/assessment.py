import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk

question_type_enum = Enum(
    "mcq", "short_answer", "numeric", "explanation", "diagram",
    name="question_type", create_type=False,
)
question_status_enum = Enum(
    "draft", "validated", "needs_repair", "invalid", "retired",
    name="question_status", create_type=False,
)
validation_verdict_enum = Enum(
    "pass", "repair_suggested", "fail", name="validation_verdict", create_type=False
)
instrument_kind_enum = Enum(
    "pretest", "posttest", "practice", name="instrument_kind", create_type=False
)
session_mode_enum = Enum(
    "adaptive", "control", "fixed_instrument", "practice",
    name="session_mode", create_type=False,
)
diagnosis_kind_enum = Enum(
    "correct_with_sound_reasoning",
    "correct_reasoning_unclear",
    "procedural_slip",
    "knowledge_gap",
    "misconception",
    "insufficient_evidence",
    name="diagnosis_kind",
    create_type=False,
)


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = uuid_pk()
    course_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(question_type_enum, nullable=False)
    stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    correct_answer: Mapped[str | None] = mapped_column(Text)
    answer_rationale: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[float | None] = mapped_column(Float)
    bloom_level: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(question_status_enum, nullable=False, default="draft")
    # The single flag that keeps pre/post-test items out of the adaptive pool.
    is_fixed_instrument: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    authored_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id")
    )
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_runs.id")
    )


class QuestionConcept(Base):
    __tablename__ = "question_concepts"

    question_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class QuestionEvidence(Base):
    __tablename__ = "question_evidence"

    question_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("source_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    quote: Mapped[str | None] = mapped_column(Text)


class QuestionValidation(Base):
    __tablename__ = "question_validations"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(validation_verdict_enum, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    checks: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id")
    )
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_runs.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AssessmentInstrument(Base):
    """A fixed pre-test or post-test. Immutable once locked_at is set."""

    __tablename__ = "assessment_instruments"

    id: Mapped[uuid.UUID] = uuid_pk()
    course_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(instrument_kind_enum, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InstrumentItem(Base):
    __tablename__ = "instrument_items"

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("assessment_instruments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("questions.id"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(session_mode_enum, nullable=False)
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("assessment_instruments.id")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("questions.id"), nullable=False
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    response_text: Mapped[str | None] = mapped_column(Text)
    response_modality: Mapped[str] = mapped_column(Text, nullable=False, default="text")
    response_media_key: Mapped[str | None] = mapped_column(Text)
    served_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AttemptAnalysis(Base):
    """What the system observed, separately from what it inferred."""

    __tablename__ = "attempt_analyses"

    id: Mapped[uuid.UUID] = uuid_pk()
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    diagnosis: Mapped[str] = mapped_column(diagnosis_kind_enum, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    observations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    inference: Mapped[str | None] = mapped_column(Text)
    alternatives: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    misconception_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("misconceptions.id")
    )
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("ai_runs.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
