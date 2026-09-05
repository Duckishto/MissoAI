from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CourseSummary(BaseModel):
    id: UUID
    slug: str
    title: str
    description: str | None = None


class QuestionOption(BaseModel):
    id: str
    text: str


class QuestionForLearner(BaseModel):
    """What the learner is allowed to see. No answer, no rationale."""

    id: UUID
    type: str
    stem: str
    options: list[QuestionOption] | None = None


class StartSessionRequest(BaseModel):
    course_id: UUID
    mode: Literal["adaptive", "control", "practice"] = "practice"


class SessionResponse(BaseModel):
    id: UUID
    course_id: UUID
    mode: str
    started_at: datetime


class NextQuestionResponse(BaseModel):
    question: QuestionForLearner | None
    decision_id: UUID
    rationale: str
    exhausted: bool = False


class SubmitAnswerRequest(BaseModel):
    question_id: UUID
    response_text: str | None = None
    response_modality: Literal["text", "image", "handwriting", "diagram"] = "text"
    response_media_key: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    hints_used: int = Field(default=0, ge=0)


class AttemptResponse(BaseModel):
    attempt_id: UUID
    recorded_at: datetime
    # Phase 0 records; it does not judge. Grading and diagnosis arrive later,
    # and the client must handle a null verdict rather than assume correctness.
    is_correct: bool | None = None
    diagnosis: str | None = None
    confidence: float | None = None
    feedback: str | None = None
    observations: list[dict[str, Any]] = []
