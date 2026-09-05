from uuid import UUID

from sqlalchemy import select

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession, RequestId
from app.models.assessment import Question
from app.models.content import Course, Enrollment
from app.modules.adaptive import selector
from app.modules.assessment import service
from app.modules.assessment.schemas import (
    AttemptResponse,
    CourseSummary,
    NextQuestionResponse,
    QuestionForLearner,
    QuestionOption,
    SessionResponse,
    StartSessionRequest,
    SubmitAnswerRequest,
)

router = APIRouter(tags=["assessment"])


@router.get("/courses", response_model=list[CourseSummary])
async def list_courses(user: CurrentUser, db: DbSession) -> list[CourseSummary]:
    rows = await db.scalars(
        select(Course)
        .join(Enrollment, Enrollment.course_id == Course.id, isouter=True)
        .where((Enrollment.user_id == user.id) | (Course.owner_id == user.id))
        .order_by(Course.title)
    )
    return [
        CourseSummary(id=c.id, slug=c.slug, title=c.title, description=c.description)
        for c in rows.unique()
    ]


@router.post(
    "/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED
)
async def start_session(
    body: StartSessionRequest, user: CurrentUser, db: DbSession, request_id: RequestId
) -> SessionResponse:
    session = await service.start_session(
        db,
        user_id=user.id,
        course_id=body.course_id,
        mode=body.mode,
        request_id=request_id,
    )
    return SessionResponse(
        id=session.id,
        course_id=session.course_id,
        mode=session.mode,
        started_at=session.started_at,
    )


@router.get("/sessions/{session_id}/next", response_model=NextQuestionResponse)
async def next_question(
    session_id: UUID, user: CurrentUser, db: DbSession
) -> NextQuestionResponse:
    session = await service.get_session(db, session_id=session_id, user_id=user.id)
    choice = await selector.select_next(
        db, session_id=session.id, course_id=session.course_id, user_id=user.id
    )
    if choice.question_id is None:
        return NextQuestionResponse(
            question=None,
            decision_id=choice.decision_id,
            rationale=choice.rationale,
            exhausted=True,
        )

    question = await db.get(Question, choice.question_id)
    assert question is not None
    options = None
    if question.options:
        options = [
            QuestionOption(id=o["id"], text=o["text"]) for o in question.options
        ]

    return NextQuestionResponse(
        question=QuestionForLearner(
            id=question.id, type=question.type, stem=question.stem, options=options
        ),
        decision_id=choice.decision_id,
        rationale=choice.rationale,
    )


@router.post(
    "/sessions/{session_id}/attempts",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_answer(
    session_id: UUID,
    body: SubmitAnswerRequest,
    user: CurrentUser,
    db: DbSession,
    request_id: RequestId,
) -> AttemptResponse:
    session = await service.get_session(db, session_id=session_id, user_id=user.id)
    attempt = await service.record_attempt(
        db,
        session=session,
        question_id=body.question_id,
        response_text=body.response_text,
        response_modality=body.response_modality,
        response_media_key=body.response_media_key,
        latency_ms=body.latency_ms,
        hints_used=body.hints_used,
        request_id=request_id,
    )
    # Phase 0 stores the response and says so. No verdict, no diagnosis.
    return AttemptResponse(
        attempt_id=attempt.id,
        recorded_at=attempt.created_at,
        is_correct=None,
        diagnosis=None,
        confidence=None,
        feedback=None,
        observations=[],
    )
