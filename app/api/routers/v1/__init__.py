from fastapi import APIRouter

from app.api.routers.v1.auth import router as auth_router
from app.api.routers.v1.users import router as users_router
from app.core.config import settings

router = APIRouter(prefix=settings.api.v1_prefix)
router.include_router(auth_router)
router.include_router(users_router)
