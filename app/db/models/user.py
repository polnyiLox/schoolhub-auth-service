from sqlalchemy import BigInteger, Boolean, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.enums import GlobalRole


class UserORM(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_telegram_id", "telegram_id", unique=True),)

    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(128))
    global_role: Mapped[GlobalRole] = mapped_column(
        Enum(GlobalRole, name="global_role"),
        nullable=False,
        default=GlobalRole.USER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
