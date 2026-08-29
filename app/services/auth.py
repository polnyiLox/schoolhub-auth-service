import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import AUTH_SUCCESSES, REFRESH_ROTATIONS
from app.enums import GlobalRole
from app.exceptions import InvalidRefreshTokenError, UserInactiveError, UserNotFoundError
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas import AuthResult, RefreshTokenRequest, TelegramLogin, TokenPair, UserRead
from app.security import AuthSecurityProvider

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        security: AuthSecurityProvider,
        admin_telegram_ids: set[int],
    ) -> None:
        self._session = session
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._security = security
        self._admin_telegram_ids = admin_telegram_ids

    async def authenticate_telegram(self, request: TelegramLogin) -> AuthResult:
        logger.info("Starting Telegram authentication")
        identity = await self._security.validate_telegram_init_data(
            request.init_data.get_secret_value()
        )

        async with self._session.begin():
            user = await self._users.get_by_telegram_id(identity.telegram_id)
            if user is None:
                role = (
                    GlobalRole.ADMIN
                    if identity.telegram_id in self._admin_telegram_ids
                    else GlobalRole.USER
                )
                user = await self._users.create(identity, role)
                logger.info("User registered: user_id=%s", user.id)
            else:
                if not user.is_active:
                    logger.warning("Authentication denied for inactive user: user_id=%s", user.id)
                    raise UserInactiveError
                user = await self._users.update_identity(user, identity)
            issued = await self._security.issue_token_pair(user)
            await self._refresh_tokens.create(
                issued.refresh_token_id,
                user.id,
                issued.refresh_expires_at,
            )

        logger.info("Telegram authentication completed: user_id=%s", user.id)
        AUTH_SUCCESSES.inc()
        return AuthResult(user=UserRead.model_validate(user), tokens=issued.tokens)

    async def refresh(self, request: RefreshTokenRequest) -> TokenPair:
        claims = await self._security.decode_refresh_token(request.refresh_token.get_secret_value())
        invalid = False
        issued = None
        async with self._session.begin():
            stored = await self._refresh_tokens.get_for_update(claims.token_id)
            if (
                stored is None
                or stored.user_id != claims.user_id
                or stored.expires_at <= datetime.now(UTC)
            ):
                invalid = True
            elif stored.revoked_at is not None:
                await self._refresh_tokens.revoke_all_for_user(claims.user_id)
                invalid = True
            else:
                user = await self._users.get(claims.user_id)
                if user is None:
                    raise UserNotFoundError
                if not user.is_active:
                    raise UserInactiveError
                issued = await self._security.issue_token_pair(user)
                await self._refresh_tokens.create(
                    issued.refresh_token_id,
                    user.id,
                    issued.refresh_expires_at,
                )
                revoked = await self._refresh_tokens.revoke(
                    claims.token_id,
                    replaced_by_id=issued.refresh_token_id,
                )
                if not revoked:
                    invalid = True

        if invalid or issued is None:
            raise InvalidRefreshTokenError
        logger.info("Refresh token rotated: user_id=%s", claims.user_id)
        REFRESH_ROTATIONS.inc()
        return issued.tokens

    async def logout(self, request: RefreshTokenRequest) -> None:
        claims = await self._security.decode_refresh_token(request.refresh_token.get_secret_value())
        async with self._session.begin():
            await self._refresh_tokens.revoke(claims.token_id)
        logger.info("Refresh token revoked: user_id=%s", claims.user_id)
