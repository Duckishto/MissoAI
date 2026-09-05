from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import Conflict, Unauthorized
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.models.identity import RefreshToken, User


async def register(
    db: AsyncSession, *, email: str, password: str, display_name: str
) -> User:
    existing = await db.scalar(
        select(User).where(func.lower(User.email) == email.lower())
    )
    if existing is not None:
        raise Conflict("An account with that email already exists.")

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        role="student",
    )
    db.add(user)
    await db.flush()
    return user


# Verified against when no user matches, so a missing account and a wrong
# password cost the same time and cannot be told apart by a stopwatch.
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not ok or not user.is_active:
        raise Unauthorized("Email or password is incorrect.")
    return user


async def issue_refresh_token(db: AsyncSession, user: User) -> str:
    settings = get_settings()
    raw, digest = new_refresh_token()
    now = datetime.now(UTC)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest,
            issued_at=now,
            expires_at=now + timedelta(seconds=settings.refresh_token_ttl_seconds),
        )
    )
    return raw


async def rotate_refresh_token(db: AsyncSession, raw: str) -> tuple[User, str, str]:
    digest = hash_refresh_token(raw)
    token = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest))
    now = datetime.now(UTC)
    if token is None or token.revoked_at is not None or token.expires_at <= now:
        raise Unauthorized("Your session expired. Sign in again.")

    token.revoked_at = now
    user = await db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise Unauthorized("Your session expired. Sign in again.")

    new_raw = await issue_refresh_token(db, user)
    return user, create_access_token(str(user.id), user.role), new_raw


async def revoke_all(db: AsyncSession, user: User) -> None:
    now = datetime.now(UTC)
    tokens = await db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    )
    for token in tokens:
        token.revoked_at = now
