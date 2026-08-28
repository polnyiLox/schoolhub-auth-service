from app.db.models import UserORM
from app.exceptions import SecurityProviderNotConfiguredError
from app.schemas import CurrentPrincipal, TelegramIdentity, TokenPair


class AuthSecurityProvider:
    """Fail-closed extension point for user-owned Telegram and JWT cryptography."""

    async def validate_telegram_init_data(self, init_data: str) -> TelegramIdentity:
        del init_data
        raise SecurityProviderNotConfiguredError

    async def issue_token_pair(self, user: UserORM) -> TokenPair:
        del user
        raise SecurityProviderNotConfiguredError

    async def verify_access_token(self, token: str) -> CurrentPrincipal:
        del token
        raise SecurityProviderNotConfiguredError


auth_security_provider = AuthSecurityProvider()
