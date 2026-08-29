from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RefreshTokenORM


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, token_id: UUID, user_id: UUID, expires_at: datetime) -> RefreshTokenORM:
        token = RefreshTokenORM(
            id=token_id,
            user_id=user_id,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_for_update(self, token_id: UUID) -> RefreshTokenORM | None:
        query = select(RefreshTokenORM).where(RefreshTokenORM.id == token_id).with_for_update()
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: UUID, *, replaced_by_id: UUID | None = None) -> bool:
        statement = (
            update(RefreshTokenORM)
            .where(RefreshTokenORM.id == token_id, RefreshTokenORM.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC), replaced_by_id=replaced_by_id)
        )
        result = cast(CursorResult[Any], await self._session.execute(statement))
        return bool(result.rowcount)

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        statement = (
            update(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == user_id, RefreshTokenORM.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        result = cast(CursorResult[Any], await self._session.execute(statement))
        return int(result.rowcount)

    async def delete_expired(self, before: datetime) -> int:
        statement = delete(RefreshTokenORM).where(RefreshTokenORM.expires_at < before)
        result = cast(CursorResult[Any], await self._session.execute(statement))
        return int(result.rowcount)
