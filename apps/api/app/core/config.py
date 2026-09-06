from functools import lru_cache
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq understands these; asyncpg does not. Managed providers such as Neon
# and Supabase hand out libpq-style URLs, so they get stripped and translated
# rather than passed through.
_LIBPQ_ONLY_PARAMS = {
    "sslmode",
    "channel_binding",
    "sslrootcert",
    "sslcert",
    "sslkey",
    "sslpassword",
    "gssencmode",
    "target_session_attrs",
}


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

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: Any) -> Any:
        """Accept a JSON array, a comma-separated list, or a single origin.

        Wrangler vars are plain strings. Requiring JSON here means a missing
        pair of brackets crashes the app on import, the port never opens, and
        the platform reports only that the container is not running.
        """
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            return text
        return [part.strip() for part in text.split(",") if part.strip()]

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
        """asyncpg URL with libpq-only query parameters removed.

        A Neon or Supabase string arrives as
        `postgresql://...?sslmode=require&channel_binding=require`, and asyncpg
        raises `TypeError: connect() got an unexpected keyword argument
        'sslmode'` on it. TLS is carried by `db_connect_args` instead.
        """
        parts = urlsplit(str(self.database_url))
        kept = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k.lower() not in _LIBPQ_ONLY_PARAMS
        ]
        return urlunsplit(
            ("postgresql+asyncpg", parts.netloc, parts.path, urlencode(kept), parts.fragment)
        )

    @property
    def alembic_url(self) -> str:
        """Synchronous psycopg URL, used only for migrations.

        asyncpg sends every statement as a prepared statement, and Postgres
        rejects multi-statement SQL in that form. psycopg uses the simple query
        protocol and reads libpq parameters such as sslmode straight from the
        URL, so nothing needs stripping here.
        """
        return str(self.database_url).replace("postgresql://", "postgresql+psycopg://", 1)

    @property
    def db_connect_args(self) -> dict[str, Any]:
        """TLS settings translated into what asyncpg expects."""
        query = dict(parse_qsl(urlsplit(str(self.database_url)).query))
        mode = query.get("sslmode", "").lower()
        if mode == "disable":
            return {}
        if mode:
            # verify-ca and verify-full need a root certificate to be supplied;
            # require is the right default for a managed provider.
            return {"ssl": "require"}
        return {}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
