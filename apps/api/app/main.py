from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import dispose_engine, get_sessionmaker
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.modules.assessment.router import router as assessment_router
from app.modules.auth.router import router as auth_router
from app.modules.research.router import router as research_router

log = get_logger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    log.info(
        "starting",
        environment=settings.environment,
        ai_enabled=settings.ai_enabled,
    )
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Adaptive Assessment API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )
    install_error_handlers(app)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        """Liveness. Must not touch the database, or a cold container looks dead."""
        return {"status": "ok", "version": app.version}

    @app.get("/health/ready", tags=["ops"])
    async def ready() -> dict[str, str]:
        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(assessment_router, prefix="/api/v1")
    app.include_router(research_router, prefix="/api/v1")
    return app


app = create_app()
