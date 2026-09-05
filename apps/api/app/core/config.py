from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from the environment. Nothing is hardcoded.

    In production these arrive as Cloudflare Container env vars, which the
    Worker injects from Wrangler secrets (see apps/api/worker/index.ts).
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Literal["local", "preview", "production"] = "local"
    app_name: str = "adaptive-assessment-api"
    log_level: str = "INFO"

    # Database ---------------------------------------------------------------
    database_url: PostgresDsn
    db_pool_size: int = 5
    db_max_overflow: int = 5
    # Containers sleep and wake; short recycle avoids serving dead connections.
    db_pool_recycle_seconds: int = 280

    # Auth -------------------------------------------------------------------
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 14
    cookie_domain: str | None = None
    cookie_secure: bool = True

    # CORS -------------------------------------------------------------------
    allowed_origins: list[str] = ["http://localhost:3000"]

    # AI ---------------------------------------------------------------------
    # Phase 0 runs with this off. Every AI call path returns fixtures instead,
    # so the whole app is developable and testable without spending tokens.
    ai_enabled: bool = False
    ai_base_url: str = "https://gateway.ai.cloudflare.com"
    ai_api_key: str | None = None
    ai_model: str = "claude-sonnet-4-6"
    ai_embedding_model: str = "text-embedding-3-small"
    ai_max_output_tokens: int = 4096

    # Object storage (R2, via the Worker's binding or S3-compatible API) -----
    media_bucket: str = "adaptive-media"
    media_endpoint: str | None = None
    media_access_key_id: str | None = None
    media_secret_access_key: str | None = None

    @property
    def sqlalchemy_url(self) -> str:
        return str(self.database_url).replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
