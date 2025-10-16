import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from main import app
from src.auth.services import create_verification_token, create_refresh_token, create_reset_password_token
from src.auth.schemas import UserCreate, PasswordResetRequest, PasswordResetConfirm
from src.auth.models import User

@pytest.mark.asyncio
async def test_signup(user_role, override_get_db, faker):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "email": faker.email(),
            "username": faker.user_name(),
            "password": faker.password(),
        }

        with patch("src.auth.routes.send_verification") as mock_send:
            response = await ac.post("/auth/signup", json=payload)
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == payload["email"]
            assert data["username"] == payload["username"]
            assert data["id"] is not None
            mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_verify_email(test_user, db_session, override_get_db):
    token = create_verification_token(test_user.email)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/auth/verify-email?token={token}")
        assert response.status_code == 200
        data = response.json()
        assert "Email verified successfully" in data.get("msg", "") or "already confirmed" in data.get("message", "")


@pytest.mark.asyncio
async def test_resend_verification(test_user, db_session, override_get_db):
    from src.auth.services import create_verification_token
    test_user.is_active = False
    db_session.add(test_user)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        with patch("src.auth.routes.send_verification") as mock_send:
            response = await ac.post("/auth/resend-verification", params={"email": test_user.email})
            assert response.status_code == 200
            data = response.json()
            assert "Verification email resent" in data["msg"]
            mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_login(test_user, user_password, override_get_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/auth/login",
            data={"username": test_user.email, "password": user_password}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_tokens(test_user, override_get_db):
    refresh_token = create_refresh_token({"sub": test_user.email})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/refresh", params={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_request_password_reset(test_user, override_get_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"email": test_user.email}

        with patch("src.auth.routes.send_reset_password") as mock_send:
            response = await ac.post("/auth/reset-password", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["msg"] == "Password reset email sent"
            mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_confirm(test_user, override_get_db, faker):
    new_password = faker.password()
    reset_token = await create_reset_password_token(test_user.email)

    with patch("src.auth.services.redis.get", new_callable=AsyncMock) as mock_redis_get, \
         patch("src.auth.routes.send_reset_password") as mock_send:
        mock_redis_get.return_value = test_user.email.encode()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/auth/reset-password/confirm", json={
                "token": reset_token,
                "new_password": new_password
            })

        assert response.status_code == 200
        data = response.json()
        assert data["msg"] == "Password updated successfully"