import logging
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.types import ExceptionHandler

from app.exceptions import (
    AccessDeniedError,
    AppError,
    AuthenticationError,
    SecurityProviderNotConfiguredError,
    SelfDeactivationError,
    UserInactiveError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

ERROR_STATUS: dict[type[AppError], int] = {
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AccessDeniedError: status.HTTP_403_FORBIDDEN,
    UserInactiveError: status.HTTP_403_FORBIDDEN,
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    SelfDeactivationError: status.HTTP_409_CONFLICT,
    SecurityProviderNotConfiguredError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    status_code = ERROR_STATUS.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    if status_code >= 500:
        logger.error("Application error: code=%s", exc.code)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, cast(ExceptionHandler, app_error_handler))
