import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI, Depends

from harness.auth.jwt import CurrentUser, get_current_user, get_optional_user
from harness.config import settings

# Create a test app with protected endpoint
test_app = FastAPI()


@test_app.get("/protected")
async def protected(user: CurrentUser = Depends(get_current_user)):
    return {"user_id": user.user_id, "email": user.email}


@test_app.get("/optional")
async def optional(user: CurrentUser | None = Depends(get_optional_user)):
    if user is None:
        return {"user": None}
    return {"user_id": user.user_id}


def _make_token(**claims) -> str:
    return pyjwt.encode(claims, settings.jwt_secret, algorithm="HS256")


@pytest.mark.asyncio
async def test_valid_token() -> None:
    token = _make_token(
        sub="user-1", email="test@example.com", name="Test", provider="github"
    )
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "user-1"
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_missing_token() -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/protected")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token() -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/protected", headers={"Authorization": "Bearer invalid.token.here"}
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_optional_user_no_token() -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/optional")
    assert resp.status_code == 200
    assert resp.json()["user"] is None


@pytest.mark.asyncio
async def test_optional_user_valid_token() -> None:
    token = _make_token(
        sub="user-2", email="test2@example.com", name="Test2", provider="google"
    )
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/optional", headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "user-2"
