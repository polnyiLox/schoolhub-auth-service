from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import RefreshTokenORM
from app.enums import GlobalRole
from app.exceptions import InvalidRefreshTokenError, UserInactiveError
from app.schemas import (
    IssuedTokenPair,
    RefreshTokenClaims,
    RefreshTokenRequest,
    TelegramIdentity,
    TelegramLogin,
    TokenPair,
)
from app.services import AuthService


def make_service(session, users, refresh_tokens, security, admins=None) -> AuthService:
    return AuthService(session, users, refresh_tokens, security, admins or set())


def issued_tokens() -> IssuedTokenPair:
    return IssuedTokenPair(
        tokens=TokenPair(access_token="access", refresh_token="refresh", expires_in=900),
        refresh_token_id=uuid4(),
        refresh_expires_at=datetime.now(UTC) + timedelta(days=1),
    )


@pytest.mark.asyncio
async def test_registers_new_regular_user(session, users, refresh_tokens, security, user):
    identity = TelegramIdentity(telegram_id=100, first_name="Sasha")
    users.get_by_telegram_id.return_value = None
    users.create.return_value = user
    security.validate_telegram_init_data.return_value = identity
    security.issue_token_pair.return_value = issued_tokens()
    result = await make_service(session, users, refresh_tokens, security).authenticate_telegram(
        TelegramLogin(init_data="signed")
    )
    users.create.assert_awaited_once_with(identity, GlobalRole.USER)
    refresh_tokens.create.assert_awaited_once()
    assert result.tokens.access_token == "access"


@pytest.mark.asyncio
async def test_registers_configured_admin(session, users, refresh_tokens, security, user):
    identity = TelegramIdentity(telegram_id=100, first_name="Sasha")
    user.global_role = GlobalRole.ADMIN
    users.get_by_telegram_id.return_value = None
    users.create.return_value = user
    security.validate_telegram_init_data.return_value = identity
    security.issue_token_pair.return_value = issued_tokens()
    await make_service(session, users, refresh_tokens, security, {100}).authenticate_telegram(
        TelegramLogin(init_data="signed")
    )
    users.create.assert_awaited_once_with(identity, GlobalRole.ADMIN)


@pytest.mark.asyncio
async def test_existing_user_identity_is_refreshed(session, users, refresh_tokens, security, user):
    identity = TelegramIdentity(telegram_id=100, username="new", first_name="New")
    users.get_by_telegram_id.return_value = user
    users.update_identity.return_value = user
    security.validate_telegram_init_data.return_value = identity
    security.issue_token_pair.return_value = issued_tokens()
    await make_service(session, users, refresh_tokens, security).authenticate_telegram(
        TelegramLogin(init_data="signed")
    )
    users.update_identity.assert_awaited_once_with(user, identity)


@pytest.mark.asyncio
async def test_inactive_user_is_rejected(session, users, refresh_tokens, security, user):
    user.is_active = False
    users.get_by_telegram_id.return_value = user
    security.validate_telegram_init_data.return_value = TelegramIdentity(
        telegram_id=100, first_name="Sasha"
    )
    with pytest.raises(UserInactiveError):
        await make_service(session, users, refresh_tokens, security).authenticate_telegram(
            TelegramLogin(init_data="signed")
        )
    security.issue_token_pair.assert_not_awaited()


@pytest.mark.asyncio
async def test_security_failure_prevents_database_access(session, users, refresh_tokens, security):
    security.validate_telegram_init_data.side_effect = RuntimeError("invalid")
    with pytest.raises(RuntimeError):
        await make_service(session, users, refresh_tokens, security).authenticate_telegram(
            TelegramLogin(init_data="bad")
        )
    users.get_by_telegram_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_rotates_stored_token(session, users, refresh_tokens, security, user):
    old_id = uuid4()
    claims = RefreshTokenClaims(
        user_id=user.id,
        token_id=old_id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    stored = RefreshTokenORM(
        id=old_id,
        user_id=user.id,
        expires_at=claims.expires_at,
        revoked_at=None,
        replaced_by_id=None,
        created_at=datetime.now(UTC),
    )
    security.decode_refresh_token.return_value = claims
    security.issue_token_pair.return_value = issued_tokens()
    refresh_tokens.get_for_update.return_value = stored
    refresh_tokens.revoke.return_value = True
    users.get.return_value = user
    result = await make_service(session, users, refresh_tokens, security).refresh(
        RefreshTokenRequest(refresh_token="old")
    )
    assert result.access_token == "access"
    refresh_tokens.revoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_reused_refresh_revokes_user_sessions(session, users, refresh_tokens, security, user):
    claims = RefreshTokenClaims(
        user_id=user.id,
        token_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    refresh_tokens.get_for_update.return_value = RefreshTokenORM(
        id=claims.token_id,
        user_id=user.id,
        expires_at=claims.expires_at,
        revoked_at=datetime.now(UTC),
        replaced_by_id=uuid4(),
        created_at=datetime.now(UTC),
    )
    security.decode_refresh_token.return_value = claims
    with pytest.raises(InvalidRefreshTokenError):
        await make_service(session, users, refresh_tokens, security).refresh(
            RefreshTokenRequest(refresh_token="reused")
        )
    refresh_tokens.revoke_all_for_user.assert_awaited_once_with(user.id)


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(session, users, refresh_tokens, security, user):
    claims = RefreshTokenClaims(
        user_id=user.id,
        token_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    security.decode_refresh_token.return_value = claims
    await make_service(session, users, refresh_tokens, security).logout(
        RefreshTokenRequest(refresh_token="token")
    )
    refresh_tokens.revoke.assert_awaited_once_with(claims.token_id)
