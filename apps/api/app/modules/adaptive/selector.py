"""Question selection.

Phase 0 selects the next unseen validated question in creation order. It is
deliberately dull, but it writes a full selection_decisions row, so the replay
harness and the audit trail are exercised before any real policy exists.

Two invariants that must survive every future policy:
  - the pool is `adaptive_question_pool`, a view that excludes fixed
    instrument items, so pre/post-test material can never be served here;
  - the seed and the learner snapshot are recorded before the choice is
    returned, so the decision can be replayed exactly.
"""

import random
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import SelectionDecision

POLICY_NAME = "sequential"
POLICY_VERSION = "0.1.0"

_POOL_SQL = text(
    """
    SELECT p.id, p.stem, p.difficulty
    FROM adaptive_question_pool p
    WHERE p.course_id = :course_id
      AND p.id NOT IN (
          SELECT a.question_id FROM attempts a WHERE a.session_id = :session_id
      )
    ORDER BY p.created_at
    LIMIT 20
    """
)


@dataclass(slots=True)
class Selection:
    question_id: UUID | None
    decision_id: UUID
    rationale: str


async def select_next(
    db: AsyncSession, *, session_id: UUID, course_id: UUID, user_id: UUID
) -> Selection:
    rows = (
        await db.execute(_POOL_SQL, {"course_id": course_id, "session_id": session_id})
    ).mappings().all()

    seed = random.getrandbits(63)
    candidates = [
        {"question_id": str(r["id"]), "score": 1.0 - i * 0.01, "components": {"order": i}}
        for i, r in enumerate(rows)
    ]
    chosen = rows[0]["id"] if rows else None
    rationale = (
        "First unseen validated question in the course pool."
        if chosen
        else "No unseen validated questions remain in the adaptive pool."
    )

    decision = SelectionDecision(
        session_id=session_id,
        chosen_question_id=chosen,
        policy_name=POLICY_NAME,
        policy_version=POLICY_VERSION,
        rng_seed=seed,
        learner_snapshot={"phase": 0, "note": "learner model not consulted yet"},
        candidates=candidates,
        rationale=rationale,
    )
    db.add(decision)
    await db.flush()

    return Selection(question_id=chosen, decision_id=decision.id, rationale=rationale)
