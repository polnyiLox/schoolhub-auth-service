import pytest
from pydantic import ValidationError

from app.exceptions import SecurityProviderNotConfiguredError
from app.schemas import TelegramIdentity, TelegramLogin, TokenPair
from app.security import AuthSecurityProvider


def test_login_hides_init_data_in_repr():
    request = TelegramLogin(init_data="secret")
    assert "secret" not in repr(request)


def test_telegram_id_must_be_positive():
    with pytest.raises(ValidationError):
        TelegramIdentity(telegram_id=0, first_name="Sasha")


def test_first_name_cannot_be_empty():
    with pytest.raises(ValidationError):
        TelegramIdentity(telegram_id=1, first_name="")


def test_token_expiry_must_be_positive():
    with pytest.raises(ValidationError):
        TokenPair(access_token="a", refresh_token="r", expires_in=0)


@pytest.mark.asyncio
async def test_default_provider_rejects_telegram_validation():
    with pytest.raises(SecurityProviderNotConfiguredError):
        await AuthSecurityProvider().validate_telegram_init_data("data")


@pytest.mark.asyncio
async def test_default_provider_rejects_token_issuance(user):
    with pytest.raises(SecurityProviderNotConfiguredError):
        await AuthSecurityProvider().issue_token_pair(user)


@pytest.mark.asyncio
async def test_default_provider_rejects_token_verification():
    with pytest.raises(SecurityProviderNotConfiguredError):
        await AuthSecurityProvider().verify_access_token("token")
