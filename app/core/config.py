from functools import lru_cache
from urllib.parse import quote

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    user: str = Field(min_length=1)
    password: str = Field(min_length=1)
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65_535)
    name: str = Field(min_length=1)
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=20, ge=0)
    pool_recycle_seconds: int = Field(default=1_800, ge=1)

    @property
    def url(self) -> str:
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        database = quote(self.name, safe="")
        return f"postgresql+asyncpg://{user}:{password}@{self.host}:{self.port}/{database}"


class ApiSettings(BaseModel):
    v1_prefix: str = Field(pattern=r"^/[^/].*$")
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65_535)
    reload: bool


class MiddlewareSettings(BaseModel):
    allow_origins: list[str]
    allow_methods: list[str]
    allow_headers: list[str]
    allow_credentials: bool


class Settings(BaseSettings):
    db: DatabaseSettings
    api: ApiSettings
    middleware: MiddlewareSettings
    admin_telegram_ids: set[int] = Field(default_factory=set)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
