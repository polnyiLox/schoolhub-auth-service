from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.exceptions import AuthenticationError
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas import CurrentPrincipal
from app.security import auth_security_provider
from app.services import AuthService, UserService

SessionDep = Annotated[AsyncSession, Depends(get_session)]
bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(session: SessionDep) -> UserRepository:
    return UserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_refresh_token_repository(session: SessionDep) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


RefreshTokenRepositoryDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)]


def get_auth_service(
    session: SessionDep,
    users: UserRepositoryDep,
    refresh_tokens: RefreshTokenRepositoryDep,
) -> AuthService:
    return AuthService(
        session=session,
        users=users,
        refresh_tokens=refresh_tokens,
        security=auth_security_provider,
        admin_telegram_ids=settings.admin_telegram_ids,
    )


def get_user_service(session: SessionDep, users: UserRepositoryDep) -> UserService:
    return UserService(session=session, users=users)


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError
    return await auth_security_provider.verify_access_token(credentials.credentials)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
CurrentPrincipalDep = Annotated[CurrentPrincipal, Depends(get_current_principal)]
