import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError
from pydantic import ValidationError

from app.core.config import SecuritySettings, settings
from app.db.models import UserORM
from app.enums import GlobalRole
from app.exceptions import AuthenticationError, InvalidRefreshTokenError
from app.schemas import (
    CurrentPrincipal,
    IssuedTokenPair,
    RefreshTokenClaims,
    TelegramIdentity,
    TokenPair,
)

logger = logging.getLogger(__name__)


class AuthSecurityProvider:
    def __init__(self, config: SecuritySettings) -> None:
        self._config = config

    async def validate_telegram_init_data(self, init_data: str) -> TelegramIdentity:
        try:
            fields = dict(parse_qsl(init_data, strict_parsing=True, keep_blank_values=True))
            provided_hash = fields.pop("hash")
            auth_date = datetime.fromtimestamp(int(fields["auth_date"]), tz=UTC)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Telegram init data rejected: malformed fields")
            raise AuthenticationError from exc

        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
        secret_key = hmac.new(
            b"WebAppData",
            self._config.telegram_bot_token.get_secret_value().encode(),
            hashlib.sha256,
        ).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(calculated_hash, provided_hash):
            logger.warning("Telegram init data rejected: invalid signature")
            raise AuthenticationError

        now = datetime.now(UTC)
        age = (now - auth_date).total_seconds()
        if age < -30 or age > self._config.telegram_init_data_ttl_seconds:
            logger.warning("Telegram init data rejected: auth date outside allowed window")
            raise AuthenticationError

        try:
            user_data = json.loads(fields["user"])
            return TelegramIdentity(
                telegram_id=user_data["id"],
                username=user_data.get("username"),
                first_name=user_data["first_name"],
                last_name=user_data.get("last_name"),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Telegram init data rejected: invalid user payload")
            raise AuthenticationError from exc

    async def issue_token_pair(self, user: UserORM) -> IssuedTokenPair:
        now = datetime.now(UTC)
        access_expires = now + timedelta(seconds=self._config.access_token_ttl_seconds)
        refresh_expires = now + timedelta(seconds=self._config.refresh_token_ttl_seconds)
        refresh_id = uuid4()
        access_token = self._encode(
            {
                "sub": str(user.id),
                "telegram_id": user.telegram_id,
                "role": user.global_role.value,
                "type": "access",
                "jti": str(uuid4()),
                "iat": now,
                "exp": access_expires,
            }
        )
        refresh_token = self._encode(
            {
                "sub": str(user.id),
                "type": "refresh",
                "jti": str(refresh_id),
                "iat": now,
                "exp": refresh_expires,
            }
        )
        return IssuedTokenPair(
            tokens=TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self._config.access_token_ttl_seconds,
            ),
            refresh_token_id=refresh_id,
            refresh_expires_at=refresh_expires,
        )

    async def verify_access_token(self, token: str) -> CurrentPrincipal:
        payload = self._decode(token, expected_type="access")
        try:
            return CurrentPrincipal(
                user_id=UUID(payload["sub"]),
                telegram_id=int(payload["telegram_id"]),
                global_role=GlobalRole(payload["role"]),
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise AuthenticationError from exc

    async def decode_refresh_token(self, token: str) -> RefreshTokenClaims:
        payload = self._decode(token, expected_type="refresh")
        try:
            return RefreshTokenClaims(
                user_id=UUID(payload["sub"]),
                token_id=UUID(payload["jti"]),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise InvalidRefreshTokenError from exc

    def _encode(self, payload: dict) -> str:
        return jwt.encode(
            {**payload, "iss": self._config.jwt_issuer, "aud": self._config.jwt_audience},
            self._config.jwt_secret.get_secret_value(),
            algorithm=self._config.jwt_algorithm,
        )

    def _decode(self, token: str, *, expected_type: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self._config.jwt_secret.get_secret_value(),
                algorithms=[self._config.jwt_algorithm],
                audience=self._config.jwt_audience,
                issuer=self._config.jwt_issuer,
                options={"require": ["exp", "iat", "sub", "jti", "type"]},
            )
        except InvalidTokenError as exc:
            error = (
                InvalidRefreshTokenError() if expected_type == "refresh" else AuthenticationError()
            )
            raise error from exc
        if payload.get("type") != expected_type:
            if expected_type == "refresh":
                raise InvalidRefreshTokenError
            raise AuthenticationError
        return payload


auth_security_provider = AuthSecurityProvider(settings.security)
