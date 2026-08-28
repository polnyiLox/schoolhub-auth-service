from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.health import router as health_router
from app.exceptions import AppError

app = FastAPI()

app.include_router(health_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.middleware.allow_origins,
    allow_methods=settings.middleware.allow_methods,
    allow_headers=settings.middleware.allow_headers,
    allow_credentials=settings.middleware.allow_credentials,
)


@app.exception_handler(AppError)
async def app_errors_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
