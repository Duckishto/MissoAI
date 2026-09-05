"""Research endpoints.

Exports carry pseudonyms only. The user_id to pseudonym mapping stays in
study_participants and is never joined into an export.
"""

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, require_role

router = APIRouter(
    prefix="/research",
    tags=["research"],
    dependencies=[Depends(require_role("researcher", "admin"))],
)


@router.get("/health")
async def research_health(db: DbSession) -> dict[str, str]:
    return {"status": "ok", "note": "export endpoints land with the study protocol"}
