"""Auth round trip. Needs a live Postgres; skipped when DATABASE_URL is absent.

Run against the docker-compose database with `make test`.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_DB_TESTS"), reason="set RUN_DB_TESTS=1 with Postgres running"
)


async def test_register_login_me(client):
    email = "phase0@example.edu"
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery", "display_name": "Phase Zero"},
    )
    assert register.status_code in (201, 409)

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


async def test_me_rejects_anonymous(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
