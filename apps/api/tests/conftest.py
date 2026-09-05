import os  # noqa: E402 - env must be set before app import

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/adaptive_test")
os.environ.setdefault("JWT_SECRET", "test-secret-value-at-least-32-characters")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("AI_ENABLED", "false")
os.environ.setdefault("COOKIE_SECURE", "false")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import create_app  # noqa: E402


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
