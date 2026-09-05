from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden, NotFound
from app.models.assessment import Attempt, Question, Session
from app.models.audit import Interaction
from app.models.content import Course, Enrollment


async def log_event(
    db: AsyncSession,
    *,
    event_type: str,
    user_id: UUID | None = None,
    session_id: UUID | None = None,
    payload: dict | None = None,
    request_id: str | None = None,
) -> None:
    db.add(
        Interaction(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            payload=payload or {},
            request_id=request_id,
        )
    )


async def assert_enrolled(db: AsyncSession, *, user_id: UUID, course_id: UUID) -> Course:
    course = await db.get(Course, course_id)
    if course is None:
        raise NotFound("That course does not exist.")
    if course.owner_id == user_id:
        return course
    enrolled = await db.get(Enrollment, (course_id, user_id))
    if enrolled is None:
        raise Forbidden("You are not enrolled in this course.")
    return course


async def start_session(
    db: AsyncSession, *, user_id: UUID, course_id: UUID, mode: str, request_id: str
) -> Session:
    await assert_enrolled(db, user_id=user_id, course_id=course_id)
    session = Session(user_id=user_id, course_id=course_id, mode=mode)
    db.add(session)
    await db.flush()
    await log_event(
        db,
        event_type="session_started",
        user_id=user_id,
        session_id=session.id,
        payload={"mode": mode, "course_id": str(course_id)},
        request_id=request_id,
    )
    return session


async def get_session(db: AsyncSession, *, session_id: UUID, user_id: UUID) -> Session:
    session = await db.get(Session, session_id)
    if session is None:
        raise NotFound("That session does not exist.")
    if session.user_id != user_id:
        raise Forbidden("That session belongs to someone else.")
    return session


async def record_attempt(
    db: AsyncSession,
    *,
    session: Session,
    question_id: UUID,
    response_text: str | None,
    response_modality: str,
    response_media_key: str | None,
    latency_ms: int | None,
    hints_used: int,
    request_id: str,
) -> Attempt:
    question = await db.get(Question, question_id)
    if question is None or question.course_id != session.course_id:
        raise NotFound("That question is not part of this session's course.")

    prior = await db.scalar(
        select(Attempt)
        .where(Attempt.session_id == session.id, Attempt.question_id == question_id)
        .order_by(Attempt.attempt_no.desc())
        .limit(1)
    )
    attempt = Attempt(
        session_id=session.id,
        user_id=session.user_id,
        question_id=question_id,
        attempt_no=(prior.attempt_no + 1) if prior else 1,
        response_text=response_text,
        response_modality=response_modality,
        response_media_key=response_media_key,
        submitted_at=datetime.now(UTC),
        latency_ms=latency_ms,
        hints_used=hints_used,
        # Left null on purpose. Phase 2 grades; Phase 0 must not guess.
        is_correct=None,
        score=None,
    )
    db.add(attempt)
    await db.flush()

    await log_event(
        db,
        event_type="attempt_submitted",
        user_id=session.user_id,
        session_id=session.id,
        payload={
            "question_id": str(question_id),
            "attempt_no": attempt.attempt_no,
            "modality": response_modality,
            "latency_ms": latency_ms,
            "hints_used": hints_used,
        },
        request_id=request_id,
    )
    return attempt
