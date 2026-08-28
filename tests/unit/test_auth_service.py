import pytest

from app.enums import GlobalRole
from app.exceptions import UserInactiveError
from app.schemas import TelegramIdentity, TelegramLogin, TokenPair
from app.services import AuthService


def make_service(session, users, security, admins: set[int] | None = None) -> AuthService:
    return AuthService(session, users, security, admins or set())


@pytest.mark.asyncio
async def test_registers_new_regular_user(session, users, security, user):
    identity = TelegramIdentity(telegram_id=100, first_name="Sasha")
    users.get_by_telegram_id.return_value = None
    users.create.return_value = user
    security.validate_telegram_init_data.return_value = identity
    security.issue_token_pair.return_value = TokenPair(
        access_token="access", refresh_token="refresh", expires_in=900
    )

    result = await make_service(session, users, security).authenticate_telegram(
        TelegramLogin(init_data="signed")
    )

    users.create.assert_awaited_once_with(identity, GlobalRole.USER)
    assert result.user.id == user.id
    assert result.tokens.access_token == "access"


@pytest.mark.asyncio
async def test_registers_configured_admin(session, users, security, user):
    identity = TelegramIdentity(telegram_id=100, first_name="Sasha")
    user.global_role = GlobalRole.ADMIN
    users.get_by_telegram_id.return_value = None
    users.create.return_value = user
    security.validate_telegram_init_data.return_value = identity
    security.issue_token_pair.return_value = TokenPair(
        access_token="a", refresh_token="r", expires_in=1
    )

    await make_service(session, users, security, {100}).authenticate_telegram(
        TelegramLogin(init_data="signed")
    )

    users.create.assert_awaited_once_with(identity, GlobalRole.ADMIN)


@pytest.mark.asyncio
async def test_existing_user_identity_is_refreshed(session, users, security, user):
    identity = TelegramIdentity(telegram_id=100, username="new", first_name="New")
    users.get_by_telegram_id.return_value = user
    users.update_identity.return_value = user
    security.validate_telegram_init_data.return_value = identity
    security.issue_token_pair.return_value = TokenPair(
        access_token="a", refresh_token="r", expires_in=1
    )

    await make_service(session, users, security).authenticate_telegram(
        TelegramLogin(init_data="signed")
    )

    users.update_identity.assert_awaited_once_with(user, identity)


@pytest.mark.asyncio
async def test_inactive_user_is_rejected(session, users, security, user):
    user.is_active = False
    users.get_by_telegram_id.return_value = user
    security.validate_telegram_init_data.return_value = TelegramIdentity(
        telegram_id=100, first_name="Sasha"
    )

    with pytest.raises(UserInactiveError):
        await make_service(session, users, security).authenticate_telegram(
            TelegramLogin(init_data="signed")
        )

    security.issue_token_pair.assert_not_awaited()


@pytest.mark.asyncio
async def test_init_data_is_passed_to_security_provider(session, users, security, user):
    users.get_by_telegram_id.return_value = user
    users.update_identity.return_value = user
    security.validate_telegram_init_data.return_value = TelegramIdentity(
        telegram_id=100, first_name="Sasha"
    )
    security.issue_token_pair.return_value = TokenPair(
        access_token="a", refresh_token="r", expires_in=1
    )

    await make_service(session, users, security).authenticate_telegram(
        TelegramLogin(init_data="signed-payload")
    )

    security.validate_telegram_init_data.assert_awaited_once_with("signed-payload")


@pytest.mark.asyncio
async def test_security_failure_prevents_database_access(session, users, security):
    security.validate_telegram_init_data.side_effect = RuntimeError("invalid")

    with pytest.raises(RuntimeError):
        await make_service(session, users, security).authenticate_telegram(
            TelegramLogin(init_data="bad")
        )

    users.get_by_telegram_id.assert_not_awaited()
