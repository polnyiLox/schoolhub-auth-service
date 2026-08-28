from uuid import uuid4

import pytest

from app.exceptions import (
    AccessDeniedError,
    SelfDeactivationError,
    UserInactiveError,
    UserNotFoundError,
)
from app.services import UserService


@pytest.mark.asyncio
async def test_get_current_returns_active_user(session, users, user, user_principal):
    user_principal.user_id = user.id
    users.get.return_value = user
    result = await UserService(session, users).get_current(user_principal)
    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_current_rejects_missing_user(session, users, user_principal):
    users.get.return_value = None
    with pytest.raises(UserNotFoundError):
        await UserService(session, users).get_current(user_principal)


@pytest.mark.asyncio
async def test_get_current_rejects_inactive_user(session, users, user, user_principal):
    user.is_active = False
    users.get.return_value = user
    with pytest.raises(UserInactiveError):
        await UserService(session, users).get_current(user_principal)


@pytest.mark.asyncio
async def test_admin_can_list_users(session, users, user, admin_principal):
    users.list.return_value = ([user], 1)
    result = await UserService(session, users).list_users(admin_principal, offset=0, limit=50)
    assert result.total == 1
    users.list.assert_awaited_once_with(offset=0, limit=50)


@pytest.mark.asyncio
async def test_regular_user_cannot_list_users(session, users, user_principal):
    with pytest.raises(AccessDeniedError):
        await UserService(session, users).list_users(user_principal, offset=0, limit=50)
    users.list.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_can_deactivate_another_user(session, users, user, admin_principal):
    users.set_active.return_value = user
    result = await UserService(session, users).set_active(admin_principal, user.id, is_active=False)
    assert result.id == user.id
    users.set_active.assert_awaited_once_with(user.id, is_active=False)


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(session, users, admin_principal):
    with pytest.raises(SelfDeactivationError):
        await UserService(session, users).set_active(
            admin_principal, admin_principal.user_id, is_active=False
        )
    users.set_active.assert_not_awaited()


@pytest.mark.asyncio
async def test_status_change_for_missing_user_fails(session, users, admin_principal):
    users.set_active.return_value = None
    with pytest.raises(UserNotFoundError):
        await UserService(session, users).set_active(admin_principal, uuid4(), is_active=False)


@pytest.mark.asyncio
async def test_regular_user_cannot_change_status(session, users, user_principal):
    with pytest.raises(AccessDeniedError):
        await UserService(session, users).set_active(user_principal, uuid4(), is_active=False)
