from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentPrincipalDep, UserServiceDep
from app.schemas import UserList, UserRead, UserStatusUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
async def get_me(principal: CurrentPrincipalDep, service: UserServiceDep) -> UserRead:
    return await service.get_current(principal)


@router.get("", response_model=UserList)
async def list_users(
    principal: CurrentPrincipalDep,
    service: UserServiceDep,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> UserList:
    return await service.list_users(principal, offset=offset, limit=limit)


@router.get("/resolve", response_model=UserRead)
async def resolve_user_by_username(
    principal: CurrentPrincipalDep,
    service: UserServiceDep,
    username: str = Query(min_length=2, max_length=65, pattern=r"^@?[A-Za-z0-9_]{1,64}$"),
) -> UserRead:
    return await service.resolve_by_username(principal, username)


@router.patch("/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: UUID,
    payload: UserStatusUpdate,
    principal: CurrentPrincipalDep,
    service: UserServiceDep,
) -> UserRead:
    return await service.set_active(principal, user_id, is_active=payload.is_active)
