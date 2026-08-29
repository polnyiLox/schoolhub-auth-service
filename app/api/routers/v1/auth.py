from fastapi import APIRouter, Response, status

from app.api.dependencies import AuthServiceDep, CurrentPrincipalDep, UserServiceDep
from app.schemas import AuthResult, RefreshTokenRequest, TelegramLogin, TokenPair

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/telegram", response_model=AuthResult)
async def authenticate_telegram(payload: TelegramLogin, service: AuthServiceDep) -> AuthResult:
    return await service.authenticate_telegram(payload)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(payload: RefreshTokenRequest, service: AuthServiceDep) -> TokenPair:
    return await service.refresh(payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshTokenRequest, service: AuthServiceDep) -> Response:
    await service.logout(payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/verify", status_code=status.HTTP_204_NO_CONTENT)
async def verify_access_token(
    principal: CurrentPrincipalDep,
    users: UserServiceDep,
) -> Response:
    user = await users.get_current(principal)
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={
            "X-User-ID": str(user.id),
            "X-Telegram-ID": str(user.telegram_id),
            "X-Global-Role": user.global_role.value,
        },
    )
