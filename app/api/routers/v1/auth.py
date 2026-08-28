from fastapi import APIRouter

from app.api.dependencies import AuthServiceDep
from app.schemas import AuthResult, TelegramLogin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/telegram", response_model=AuthResult)
async def authenticate_telegram(payload: TelegramLogin, service: AuthServiceDep) -> AuthResult:
    return await service.authenticate_telegram(payload)
