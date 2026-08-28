import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import GlobalRole
from app.exceptions import UserInactiveError
from app.repositories import UserRepository
from app.schemas import AuthResult, TelegramLogin, UserRead
from app.security import AuthSecurityProvider

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        security: AuthSecurityProvider,
        admin_telegram_ids: set[int],
    ) -> None:
        self._session = session
        self._users = users
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

        tokens = await self._security.issue_token_pair(user)
        logger.info("Telegram authentication completed: user_id=%s", user.id)
        return AuthResult(user=UserRead.model_validate(user), tokens=tokens)
