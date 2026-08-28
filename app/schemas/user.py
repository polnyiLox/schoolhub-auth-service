from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import GlobalRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_id: int
    username: str | None
    first_name: str
    last_name: str | None
    global_role: GlobalRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserList(BaseModel):
    items: list[UserRead]
    total: int = Field(ge=0)


class UserStatusUpdate(BaseModel):
    is_active: bool
