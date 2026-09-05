"""The guarantee the study depends on: fixed instrument items never reach the
adaptive pool, and a locked instrument cannot be edited.

These assert against the database triggers, so they need a migrated Postgres.
"""

import os

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_DB_TESTS"), reason="set RUN_DB_TESTS=1 with Postgres running"
)


async def test_fixed_items_excluded_from_pool():
    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as db:
        leaked = await db.scalar(
            text("SELECT count(*) FROM adaptive_question_pool WHERE is_fixed_instrument")
        )
        assert leaked == 0


async def test_locked_instrument_rejects_new_items():
    from app.core.db import get_sessionmaker

    async with get_sessionmaker()() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT id FROM assessment_instruments "
                    "WHERE locked_at IS NOT NULL LIMIT 1"
                )
            )
        ).all()
        if not rows:
            pytest.skip("no locked instrument in this database yet")
        with pytest.raises(Exception, match="locked"):
            await db.execute(
                text(
                    "INSERT INTO instrument_items (instrument_id, question_id, position) "
                    "VALUES (:i, gen_random_uuid(), 999)"
                ),
                {"i": rows[0][0]},
            )
