"""Minimal dev seed: one instructor, one student, one course, three questions.

Enough to click through the Phase 0 flow end to end. Safe to re-run.

Passwords come from SEED_PASSWORD. If it is unset a random one is generated
and printed once, so a shared literal never ends up committed and then reused
against a deployment with real participants on it.
"""

import asyncio
import os
import pathlib
import secrets
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app.core.db import get_sessionmaker  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Concept,
    Course,
    Enrollment,
    Question,
    QuestionConcept,
    User,
)

QUESTIONS = [
    (
        "mcq",
        "A learner answers a hard item correctly on their first try, with no working shown. "
        "What can the system conclude about their mastery of the underlying concept?",
        [
            {"id": "a", "text": "Mastery is confirmed", "is_correct": False},
            {"id": "b", "text": "The estimate should rise, but stays uncertain", "is_correct": True},
            {"id": "c", "text": "Nothing at all can be inferred", "is_correct": False},
            {"id": "d", "text": "A misconception has been ruled out", "is_correct": False},
        ],
        "b",
    ),
    (
        "short_answer",
        "Why must a fixed post-test stay independent of the adaptive intervention?",
        None,
        None,
    ),
    (
        "mcq",
        "A student's answer is wrong but their stated reasoning is sound and the error is "
        "arithmetic. Which diagnosis fits?",
        [
            {"id": "a", "text": "Misconception", "is_correct": False},
            {"id": "b", "text": "Knowledge gap", "is_correct": False},
            {"id": "c", "text": "Procedural slip", "is_correct": True},
            {"id": "d", "text": "Insufficient evidence", "is_correct": False},
        ],
        "c",
    ),
]


async def main() -> None:
    password = os.environ.get("SEED_PASSWORD") or secrets.token_urlsafe(18)
    generated = "SEED_PASSWORD" not in os.environ

    async with get_sessionmaker()() as db:
        instructor = await db.scalar(
            select(User).where(func.lower(User.email) == "instructor@example.edu")
        )
        if instructor is None:
            instructor = User(
                email="instructor@example.edu",
                password_hash=hash_password(password),
                display_name="Dev Instructor",
                role="instructor",
            )
            db.add(instructor)
            await db.flush()

        student = await db.scalar(
            select(User).where(func.lower(User.email) == "student@example.edu")
        )
        if student is None:
            student = User(
                email="student@example.edu",
                password_hash=hash_password(password),
                display_name="Dev Student",
                role="student",
            )
            db.add(student)
            await db.flush()

        course = await db.scalar(select(Course).where(Course.slug == "demo"))
        if course is None:
            course = Course(
                owner_id=instructor.id,
                slug="demo",
                title="Adaptive assessment, demo course",
                description="Three hand-written items for walking the Phase 0 flow.",
            )
            db.add(course)
            await db.flush()
            db.add(Enrollment(course_id=course.id, user_id=student.id))

            concept = Concept(
                course_id=course.id,
                slug="evidence-and-mastery",
                canonical_name="Evidence and mastery",
                description="Mastery is a probabilistic estimate, not a verdict.",
            )
            db.add(concept)
            await db.flush()

            for qtype, stem, options, answer in QUESTIONS:
                q = Question(
                    course_id=course.id,
                    type=qtype,
                    stem=stem,
                    options=options,
                    correct_answer=answer,
                    difficulty=0.5,
                    status="validated",
                    is_fixed_instrument=False,
                    authored_by=instructor.id,
                )
                db.add(q)
                await db.flush()
                db.add(QuestionConcept(question_id=q.id, concept_id=concept.id, is_primary=True))

        await db.commit()
        print("seeded: instructor@example.edu / student@example.edu")
        if generated:
            print(f"generated password (shown once): {password}")


if __name__ == "__main__":
    asyncio.run(main())
