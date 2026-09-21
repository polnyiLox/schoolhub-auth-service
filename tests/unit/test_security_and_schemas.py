import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import SecuritySettings
from app.exceptions import AuthenticationError, InvalidRefreshTokenError
from app.schemas import TelegramIdentity, TelegramLogin, TokenPair
from app.security import AuthSecurityProvider


@pytest.fixture
def provider() -> AuthSecurityProvider:
    return AuthSecurityProvider(
        SecuritySettings(
            telegram_bot_token=SecretStr("bot-token"),
            jwt_secret=SecretStr("a-secure-test-key-with-at-least-32-characters"),
            access_token_ttl_seconds=900,
            refresh_token_ttl_seconds=3600,
            telegram_init_data_ttl_seconds=300,
        )
    )


def signed_init_data(
    *, auth_date: int | None = None, first_name: str = "Sasha", user: dict | None = None
) -> str:
    fields = {
        "auth_date": str(auth_date or int(datetime.now(UTC).timestamp())),
        "query_id": "query",
        "user": json.dumps(user or {"id": 100, "first_name": first_name}, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", b"bot-token", hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


@pytest.mark.asyncio
async def test_telegram_init_data_remains_valid_after_five_minutes():
    config = SecuritySettings(
        telegram_bot_token=SecretStr("bot-token"),
        jwt_secret=SecretStr("a-secure-test-key-with-at-least-32-characters"),
    )
    provider = AuthSecurityProvider(config)
    auth_date = int(datetime.now(UTC).timestamp()) - 3600
    identity = await provider.validate_telegram_init_data(signed_init_data(auth_date=auth_date))
    assert identity.telegram_id == 100


def test_login_hides_init_data_in_repr():
    assert "secret" not in repr(TelegramLogin(init_data="secret"))


def test_telegram_id_must_be_positive():
    with pytest.raises(ValidationError):
        TelegramIdentity(telegram_id=0, first_name="Sasha")


def test_token_expiry_must_be_positive():
    with pytest.raises(ValidationError):
        TokenPair(access_token="a", refresh_token="r", expires_in=0)


@pytest.mark.asyncio
async def test_valid_telegram_init_data_is_parsed(provider):
    identity = await provider.validate_telegram_init_data(signed_init_data())
    assert identity.telegram_id == 100
    assert identity.first_name == "Sasha"


@pytest.mark.asyncio
async def test_blank_optional_telegram_names_are_normalized(provider):
    identity = await provider.validate_telegram_init_data(
        signed_init_data(user={"id": 100, "first_name": "Sasha", "username": "", "last_name": ""})
    )
    assert identity.username is None
    assert identity.last_name is None


@pytest.mark.asyncio
async def test_missing_first_name_uses_username(provider):
    identity = await provider.validate_telegram_init_data(
        signed_init_data(user={"id": 100, "username": "sasha"})
    )
    assert identity.first_name == "sasha"


@pytest.mark.asyncio
async def test_tampered_telegram_init_data_is_rejected(provider):
    value = signed_init_data().replace("Sasha", "Alex")
    with pytest.raises(AuthenticationError):
        await provider.validate_telegram_init_data(value)


@pytest.mark.asyncio
async def test_expired_telegram_init_data_is_rejected(provider):
    expired = int(datetime.now(UTC).timestamp()) - 301
    with pytest.raises(AuthenticationError):
        await provider.validate_telegram_init_data(signed_init_data(auth_date=expired))


@pytest.mark.asyncio
async def test_access_token_round_trip(provider, user):
    issued = await provider.issue_token_pair(user)
    principal = await provider.verify_access_token(issued.tokens.access_token)
    assert principal.user_id == user.id
    assert principal.telegram_id == user.telegram_id


@pytest.mark.asyncio
async def test_refresh_token_round_trip(provider, user):
    issued = await provider.issue_token_pair(user)
    claims = await provider.decode_refresh_token(issued.tokens.refresh_token)
    assert claims.user_id == user.id
    assert claims.token_id == issued.refresh_token_id


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_access(provider, user):
    issued = await provider.issue_token_pair(user)
    with pytest.raises(AuthenticationError):
        await provider.verify_access_token(issued.tokens.refresh_token)


@pytest.mark.asyncio
async def test_access_token_cannot_be_used_as_refresh(provider, user):
    issued = await provider.issue_token_pair(user)
    with pytest.raises(InvalidRefreshTokenError):
        await provider.decode_refresh_token(issued.tokens.access_token)


@pytest.mark.asyncio
async def test_modified_jwt_is_rejected(provider, user):
    issued = await provider.issue_token_pair(user)
    header, payload, signature = issued.tokens.access_token.split(".")
    signature = ("a" if signature[0] != "a" else "b") + signature[1:]
    token = ".".join((header, payload, signature))
    with pytest.raises(AuthenticationError):
        await provider.verify_access_token(token)
