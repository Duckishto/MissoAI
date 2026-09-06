from fastapi import APIRouter, Cookie, Response, status

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.errors import Unauthorized
from app.core.security import create_access_token
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "aa_refresh"
# Must match where the router is actually mounted. A cookie scoped to /auth
# is never sent to /api/v1/auth/refresh, and the failure looks like an
# expired session rather than a misconfiguration.
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, raw: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path=REFRESH_COOKIE_PATH,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: DbSession) -> TokenResponse:
    user = await service.register(
        db, email=body.email, password=body.password, display_name=body.display_name
    )
    raw = await service.issue_refresh_token(db, user)
    _set_refresh_cookie(response, raw)
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    user = await service.authenticate(db, email=body.email, password=body.password)
    raw = await service.issue_refresh_token(db, user)
    _set_refresh_cookie(response, raw)
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: DbSession,
    aa_refresh: str | None = Cookie(default=None),
) -> TokenResponse:
    if not aa_refresh:
        raise Unauthorized("Sign in to continue.")
    _user, access, new_raw = await service.rotate_refresh_token(db, aa_refresh)
    _set_refresh_cookie(response, new_raw)
    return TokenResponse(
        access_token=access, expires_in=get_settings().access_token_ttl_seconds
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: CurrentUser, response: Response, db: DbSession) -> None:
    await service.revoke_all(db, user)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=user.id, email=user.email, display_name=user.display_name, role=user.role
    )
