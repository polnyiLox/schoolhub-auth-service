from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.enums import GlobalRole
from app.repositories import UserRepository
from app.schemas import TelegramIdentity


@pytest.mark.asyncio
async def test_get_returns_scalar(session, user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=result)
    assert await UserRepository(session).get(user.id) is user


@pytest.mark.asyncio
async def test_get_by_telegram_id_returns_none(session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)
    assert await UserRepository(session).get_by_telegram_id(100) is None


@pytest.mark.asyncio
async def test_list_returns_items_and_total(session, user):
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [user]
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    session.execute = AsyncMock(side_effect=[items_result, count_result])
    items, total = await UserRepository(session).list(offset=0, limit=10)
    assert items == [user]
    assert total == 1


@pytest.mark.asyncio
async def test_create_adds_flushes_and_refreshes(session):
    identity = TelegramIdentity(telegram_id=100, first_name="Sasha")
    user = await UserRepository(session).create(identity, GlobalRole.USER)
    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)
    assert user.telegram_id == 100


@pytest.mark.asyncio
async def test_update_identity_changes_profile(session, user):
    identity = TelegramIdentity(
        telegram_id=user.telegram_id,
        username="updated",
        first_name="Alex",
        last_name="P",
    )
    result = await UserRepository(session).update_identity(user, identity)
    assert result.username == "updated"
    assert result.first_name == "Alex"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_active_returns_updated_user(session, user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute = AsyncMock(return_value=result)
    assert await UserRepository(session).set_active(user.id, is_active=False) is user


@pytest.mark.asyncio
async def test_set_active_returns_none_for_unknown_user(session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)
    assert await UserRepository(session).set_active(uuid4(), is_active=False) is None
