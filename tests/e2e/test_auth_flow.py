from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_auth_service, get_current_principal, get_session
from app.enums import GlobalRole
from app.main import app
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas import CurrentPrincipal, IssuedTokenPair, TelegramIdentity, TokenPair
from app.security import AuthSecurityProvider
from app.services import AuthService

pytestmark = pytest.mark.e2e


class FakeSecurity(AuthSecurityProvider):
    def __init__(self):
        pass

    async def validate_telegram_init_data(self, init_data: str) -> TelegramIdentity:
        return TelegramIdentity(telegram_id=int(init_data), first_name="E2E")

    async def issue_token_pair(self, user) -> IssuedTokenPair:
        return IssuedTokenPair(
            tokens=TokenPair(access_token="access", refresh_token="refresh", expires_in=900),
            refresh_token_id=uuid4(),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=1),
        )


@pytest.mark.asyncio
async def test_admin_login_then_reads_profile(session):
    repository = UserRepository(session)
    service = AuthService(
        session,
        repository,
        RefreshTokenRepository(session),
        FakeSecurity(),
        {9_001},
    )
    principal_holder: dict[str, CurrentPrincipal] = {}

    async def session_override():
        yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_auth_service] = lambda: service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post("/v1/auth/telegram", json={"init_data": "9001"})
        user = login.json()["user"]
        principal_holder["value"] = CurrentPrincipal(
            user_id=user["id"],
            telegram_id=user["telegram_id"],
            global_role=GlobalRole(user["global_role"]),
        )
        app.dependency_overrides[get_current_principal] = lambda: principal_holder["value"]
        profile = await client.get("/v1/users/me")
    app.dependency_overrides.clear()

    assert login.status_code == 200
    assert profile.status_code == 200
    assert profile.json()["global_role"] == "admin"
