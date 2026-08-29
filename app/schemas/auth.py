from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from app.enums import GlobalRole
from app.schemas.user import UserRead


class TelegramLogin(BaseModel):
    init_data: SecretStr


class TelegramIdentity(BaseModel):
    telegram_id: int = Field(gt=0)
    username: str | None = Field(default=None, min_length=1, max_length=64)
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0)


class IssuedTokenPair(BaseModel):
    tokens: TokenPair
    refresh_token_id: UUID
    refresh_expires_at: datetime


class RefreshTokenRequest(BaseModel):
    refresh_token: SecretStr


class RefreshTokenClaims(BaseModel):
    user_id: UUID
    token_id: UUID
    expires_at: datetime


class AuthResult(BaseModel):
    user: UserRead
    tokens: TokenPair


class CurrentPrincipal(BaseModel):
    user_id: UUID
    telegram_id: int
    global_role: GlobalRole
