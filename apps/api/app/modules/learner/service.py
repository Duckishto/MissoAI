"""Mastery estimation.

Phase 0 ships the record-keeping only. The update rule below is a placeholder
that moves nothing, so no learner state can drift on untested maths. What is
real from day one is the shape of the write: current state and an append-only
history row, always together, always tagged with the model version that
produced them.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learner import LearnerState, LearnerStateHistory

MODEL_VERSION = "noop-0.1.0"


@dataclass(slots=True)
class MasteryUpdate:
    mean: float
    variance: float
    reason: str


async def get_or_create_state(
    db: AsyncSession, *, user_id: UUID, concept_id: UUID
) -> LearnerState:
    state = await db.get(LearnerState, (user_id, concept_id))
    if state is None:
        state = LearnerState(user_id=user_id, concept_id=concept_id)
        db.add(state)
        await db.flush()
    return state


def compute_update(
    state: LearnerState,
    *,
    is_correct: bool | None,
    difficulty: float | None,
    diagnosis: str | None,
    confidence: float,
) -> MasteryUpdate:
    """Placeholder. Phase 3 replaces this with the real estimator.

    Two constraints the real version must keep: weak evidence must not move
    the estimate far, and a single response must never dominate a consistent
    history. Returning the state unchanged is the honest Phase 0 behaviour.
    """
    return MasteryUpdate(
        mean=state.mastery_mean,
        variance=state.mastery_variance,
        reason="phase0_noop",
    )


async def apply_update(
    db: AsyncSession,
    *,
    user_id: UUID,
    concept_id: UUID,
    attempt_id: UUID | None,
    update: MasteryUpdate,
) -> LearnerState:
    state = await get_or_create_state(db, user_id=user_id, concept_id=concept_id)
    state.mastery_mean = update.mean
    state.mastery_variance = update.variance
    state.observations += 1
    state.last_attempt_id = attempt_id

    db.add(
        LearnerStateHistory(
            user_id=user_id,
            concept_id=concept_id,
            attempt_id=attempt_id,
            mastery_mean=update.mean,
            mastery_variance=update.variance,
            observations=state.observations,
            update_reason=update.reason,
            model_version=MODEL_VERSION,
        )
    )
    return state
