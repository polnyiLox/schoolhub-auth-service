from functools import lru_cache
from urllib.parse import quote

from pydantic import BaseModel, Field, SecretStr
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


class SecuritySettings(BaseModel):
    telegram_bot_token: SecretStr
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: str = Field(default="HS256", pattern=r"^HS(256|384|512)$")
    jwt_issuer: str = Field(default="schoolhub-auth", min_length=1)
    jwt_audience: str = Field(default="schoolhub-api", min_length=1)
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=86_400)
    refresh_token_ttl_seconds: int = Field(default=2_592_000, ge=300)
    telegram_init_data_ttl_seconds: int = Field(default=300, ge=30, le=3_600)


class Settings(BaseSettings):
    db: DatabaseSettings
    api: ApiSettings
    middleware: MiddlewareSettings
    security: SecuritySettings
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
