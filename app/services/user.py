import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserORM
from app.enums import GlobalRole
from app.exceptions import (
    AccessDeniedError,
    SelfDeactivationError,
    UserInactiveError,
    UserNotFoundError,
)
from app.repositories import UserRepository
from app.schemas import CurrentPrincipal, UserList, UserRead

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session: AsyncSession, users: UserRepository) -> None:
        self._session = session
        self._users = users

    async def get_current(self, principal: CurrentPrincipal) -> UserRead:
        user = await self._require_active_user(principal.user_id)
        return UserRead.model_validate(user)

    async def list_users(
        self,
        principal: CurrentPrincipal,
        *,
        offset: int,
        limit: int,
    ) -> UserList:
        self._require_admin(principal)
        users, total = await self._users.list(offset=offset, limit=limit)
        return UserList(items=[UserRead.model_validate(user) for user in users], total=total)

    async def resolve_by_username(
        self,
        principal: CurrentPrincipal,
        username: str,
    ) -> UserRead:
        self._require_admin(principal)
        normalized = username.strip().removeprefix("@").lower()
        user = await self._users.get_by_username(normalized)
        if user is None or not user.is_active:
            raise UserNotFoundError
        return UserRead.model_validate(user)

    async def set_active(
        self,
        principal: CurrentPrincipal,
        user_id: UUID,
        *,
        is_active: bool,
    ) -> UserRead:
        self._require_admin(principal)
        if principal.user_id == user_id and not is_active:
            raise SelfDeactivationError

        async with self._session.begin():
            user = await self._users.set_active(user_id, is_active=is_active)
            if user is None:
                raise UserNotFoundError

        logger.info(
            "User status changed: user_id=%s is_active=%s actor_user_id=%s",
            user_id,
            is_active,
            principal.user_id,
        )
        return UserRead.model_validate(user)

    async def _require_active_user(self, user_id: UUID) -> UserORM:
        user = await self._users.get(user_id)
        if user is None:
            raise UserNotFoundError
        if not user.is_active:
            raise UserInactiveError
        return user

    @staticmethod
    def _require_admin(principal: CurrentPrincipal) -> None:
        if principal.global_role is not GlobalRole.ADMIN:
            logger.warning("Admin access denied: user_id=%s", principal.user_id)
            raise AccessDeniedError
