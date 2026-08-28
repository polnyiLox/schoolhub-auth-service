from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_session
from app.main import app


async def request(path: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_liveness_is_independent_from_database():
    response = await request("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_returns_503_when_database_is_unavailable():
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("offline")
    app.dependency_overrides[get_session] = lambda: session
    try:
        response = await request("/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
