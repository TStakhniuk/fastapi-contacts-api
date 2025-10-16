import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Contacts API"}


@pytest.mark.asyncio
async def test_lifespan_startup_shutdown(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.close = AsyncMock()

    monkeypatch.setattr("main.aioredis.from_url", lambda *a, **kw: mock_redis)
    monkeypatch.setattr("main.FastAPICache.init", lambda *a, **kw: None)
    monkeypatch.setattr("main.FastAPILimiter.init", AsyncMock())

    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200

    mock_redis.close.assert_awaited_once()
