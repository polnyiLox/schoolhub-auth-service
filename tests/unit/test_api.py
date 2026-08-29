from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_auth_service, get_current_principal, get_user_service
from app.exceptions import AccessDeniedError, InvalidRefreshTokenError, UserNotFoundError
from app.main import app
from app.schemas import AuthResult, TokenPair, UserList, UserRead


@pytest.fixture
def auth_service():
    return AsyncMock()


@pytest.fixture
def user_service():
    return AsyncMock()


@pytest_asyncio.fixture
async def client(auth_service, user_service, admin_principal):
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_user_service] = lambda: user_service
    app.dependency_overrides[get_current_principal] = lambda: admin_principal
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_endpoint_returns_tokens(client, auth_service, user):
    auth_service.authenticate_telegram.return_value = AuthResult(
        user=UserRead.model_validate(user),
        tokens=TokenPair(access_token="access", refresh_token="refresh", expires_in=900),
    )
    response = await client.post("/v1/auth/telegram", json={"init_data": "signed"})
    assert response.status_code == 200
    assert response.json()["tokens"]["access_token"] == "access"


@pytest.mark.asyncio
async def test_auth_endpoint_validates_empty_payload(client):
    response = await client.post("/v1/auth/telegram", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_refresh_maps_to_401(client, auth_service):
    auth_service.refresh.side_effect = InvalidRefreshTokenError()
    response = await client.post("/v1/auth/refresh", json={"refresh_token": "invalid"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


@pytest.mark.asyncio
async def test_refresh_endpoint_returns_rotated_pair(client, auth_service):
    auth_service.refresh.return_value = TokenPair(
        access_token="new-access", refresh_token="new-refresh", expires_in=900
    )
    response = await client.post("/v1/auth/refresh", json={"refresh_token": "old"})
    assert response.status_code == 200
    assert response.json()["refresh_token"] == "new-refresh"


@pytest.mark.asyncio
async def test_logout_returns_204(client, auth_service):
    response = await client.post("/v1/auth/logout", json={"refresh_token": "token"})
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_verify_returns_trusted_identity_headers(client, user_service, user):
    user_service.get_current.return_value = UserRead.model_validate(user)
    response = await client.get("/v1/auth/verify")
    assert response.status_code == 204
    assert response.headers["X-User-ID"] == str(user.id)
    assert response.headers["X-Telegram-ID"] == str(user.telegram_id)


@pytest.mark.asyncio
async def test_get_me_returns_user(client, user_service, user):
    user_service.get_current.return_value = UserRead.model_validate(user)
    response = await client.get("/v1/users/me")
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


@pytest.mark.asyncio
async def test_list_users_returns_pagination(client, user_service, user):
    user_service.list_users.return_value = UserList(items=[UserRead.model_validate(user)], total=1)
    response = await client.get("/v1/users?offset=0&limit=10")
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_users_rejects_invalid_limit(client):
    response = await client.get("/v1/users?limit=101")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_access_denied_maps_to_403(client, user_service):
    user_service.list_users.side_effect = AccessDeniedError()
    response = await client.get("/v1/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_missing_user_maps_to_404(client, user_service):
    user_service.set_active.side_effect = UserNotFoundError()
    response = await client.patch(
        "/v1/users/00000000-0000-0000-0000-000000000001/status",
        json={"is_active": False},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_status_payload_is_required(client):
    response = await client.patch("/v1/users/00000000-0000-0000-0000-000000000001/status", json={})
    assert response.status_code == 422
