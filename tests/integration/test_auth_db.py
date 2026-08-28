from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.enums import GlobalRole
from app.repositories import UserRepository
from app.schemas import CurrentPrincipal, TelegramIdentity, TelegramLogin, TokenPair
from app.security import AuthSecurityProvider
from app.services import AuthService, UserService

pytestmark = pytest.mark.integration


class FakeSecurity(AuthSecurityProvider):
    async def validate_telegram_init_data(self, init_data: str) -> TelegramIdentity:
        return TelegramIdentity(telegram_id=int(init_data), first_name="Integration")

    async def issue_token_pair(self, user) -> TokenPair:
        return TokenPair(access_token=str(user.id), refresh_token="refresh", expires_in=900)


@pytest.mark.asyncio
async def test_repository_round_trip(session):
    repository = UserRepository(session)
    identity = TelegramIdentity(telegram_id=8_001, first_name="Repo")
    created = await repository.create(identity, GlobalRole.USER)
    loaded = await repository.get_by_telegram_id(identity.telegram_id)
    assert loaded is not None
    assert loaded.id == created.id


@pytest.mark.asyncio
async def test_database_enforces_unique_telegram_id(session):
    repository = UserRepository(session)
    identity = TelegramIdentity(telegram_id=8_002, first_name="Unique")
    await repository.create(identity, GlobalRole.USER)
    with pytest.raises(IntegrityError):
        await repository.create(identity, GlobalRole.USER)


@pytest.mark.asyncio
async def test_auth_service_persists_admin(session):
    repository = UserRepository(session)
    result = await AuthService(session, repository, FakeSecurity(), {8_003}).authenticate_telegram(
        TelegramLogin(init_data="8003")
    )
    loaded = await repository.get_by_telegram_id(8_003)
    assert result.user.global_role is GlobalRole.ADMIN
    assert loaded is not None


@pytest.mark.asyncio
async def test_user_service_reads_persisted_profile(session):
    repository = UserRepository(session)
    user = await repository.create(
        TelegramIdentity(telegram_id=8_004, first_name="Profile"), GlobalRole.USER
    )
    principal = CurrentPrincipal(
        user_id=user.id, telegram_id=user.telegram_id, global_role=user.global_role
    )
    result = await UserService(session, repository).get_current(principal)
    assert result.first_name == "Profile"


@pytest.mark.asyncio
async def test_unknown_persisted_user_is_not_returned(session):
    assert await UserRepository(session).get(uuid4()) is None
