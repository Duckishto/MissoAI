from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import session_scope
from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_token
from app.models.identity import User

bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(session_scope)]


async def current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise Unauthorized("Sign in to continue.")
    try:
        claims = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Your session expired. Sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise Unauthorized("Sign in to continue.") from exc

    user = await db.scalar(select(User).where(User.id == UUID(claims["sub"])))
    if user is None or not user.is_active:
        raise Unauthorized("Sign in to continue.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: str):
    async def _guard(user: CurrentUser) -> User:
        if user.role not in roles:
            raise Forbidden("You do not have access to this.")
        return user

    return _guard


async def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


RequestId = Annotated[str, Depends(request_id)]
