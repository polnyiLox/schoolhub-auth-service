from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserORM
from app.enums import GlobalRole
from app.schemas import TelegramIdentity


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> UserORM | None:
        query = select(UserORM).where(UserORM.id == user_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> UserORM | None:
        query = select(UserORM).where(UserORM.telegram_id == telegram_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def list(self, *, offset: int, limit: int) -> tuple[list[UserORM], int]:
        query = select(UserORM).order_by(UserORM.created_at.desc()).offset(offset).limit(limit)
        count_query = select(func.count()).select_from(UserORM)
        result = await self._session.execute(query)
        count_result = await self._session.execute(count_query)
        return list(result.scalars().all()), int(count_result.scalar_one())

    async def create(self, identity: TelegramIdentity, role: GlobalRole) -> UserORM:
        user = UserORM(**identity.model_dump(), global_role=role)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update_identity(self, user: UserORM, identity: TelegramIdentity) -> UserORM:
        user.username = identity.username
        user.first_name = identity.first_name
        user.last_name = identity.last_name
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def set_active(self, user_id: UUID, *, is_active: bool) -> UserORM | None:
        statement = (
            update(UserORM)
            .where(UserORM.id == user_id)
            .values(is_active=is_active)
            .returning(UserORM)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
