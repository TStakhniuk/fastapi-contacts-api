import io
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from main import app
from src.users.repository import UserProfileRepository
from src.auth.schemas import RoleEnum


@pytest.mark.asyncio
async def test_get_user_profile(test_user, auth_header, override_get_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/users/me", headers=auth_header)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username
    assert data["role"] == test_user.role.name


@pytest.mark.asyncio
async def test_update_avatar_user(test_user, auth_header, override_get_db):
    fake_file_content = b"fake image bytes"
    fake_file = io.BytesIO(fake_file_content)
    test_user.avatar = "http://cloudinary/fake_avatar.png"

    with patch("src.users.routes.upload_avatar", new_callable=AsyncMock) as mock_upload, \
         patch.object(UserProfileRepository, "update_avatar", new_callable=AsyncMock) as mock_update:

        mock_upload.return_value = "http://cloudinary/fake_avatar.png"
        mock_update.return_value = test_user

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            files = {"file": ("avatar.png", fake_file, "image/png")}
            response = await ac.patch("/users/avatar", headers=auth_header, files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["avatar"] == "http://cloudinary/fake_avatar.png"

        mock_upload.assert_awaited_once()
        mock_update.assert_awaited_once()
