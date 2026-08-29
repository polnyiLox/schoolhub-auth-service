from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserORM
from app.enums import GlobalRole
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas import CurrentPrincipal
from app.security import AuthSecurityProvider


@pytest.fixture
def user() -> UserORM:
    now = datetime.now(UTC)
    return UserORM(
        id=uuid4(),
        telegram_id=100,
        username="student",
        first_name="Sasha",
        last_name=None,
        global_role=GlobalRole.USER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def admin_principal() -> CurrentPrincipal:
    return CurrentPrincipal(user_id=uuid4(), telegram_id=1, global_role=GlobalRole.ADMIN)


@pytest.fixture
def user_principal() -> CurrentPrincipal:
    return CurrentPrincipal(user_id=uuid4(), telegram_id=2, global_role=GlobalRole.USER)


@pytest.fixture
def session() -> MagicMock:
    value = MagicMock(spec=AsyncSession)
    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    value.begin.return_value = transaction
    return value


@pytest.fixture
def users() -> AsyncMock:
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def refresh_tokens() -> AsyncMock:
    return AsyncMock(spec=RefreshTokenRepository)


@pytest.fixture
def security() -> AsyncMock:
    return AsyncMock(spec=AuthSecurityProvider)
