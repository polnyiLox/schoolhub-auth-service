# SchoolHub Auth Service

Сервис идентификации пользователей SchoolHub. Он хранит связь между Telegram-пользователем и
глобальной ролью (`ADMIN`/`USER`), выдаёт профиль текущего пользователя и позволяет администратору
включать или отключать аккаунты.

## Архитектура

```text
HTTP API -> Auth/User Service -> User Repository -> PostgreSQL
                     |
                     -> AuthSecurityProvider (точка расширения)
```

`AuthSecurityProvider` намеренно работает в режиме fail-closed. Криптографическую проверку Telegram
`initData`, подпись JWT и проверку JWT необходимо реализовать в
`app/security/provider.py`. До этого `POST /v1/auth/telegram` и Bearer-аутентификация возвращают
`503`, а не принимают неподтверждённые данные.

## API

- `POST /v1/auth/telegram` — проверка Telegram initData, регистрация/обновление профиля, выдача токенов;
- `GET /v1/users/me` — профиль текущего пользователя;
- `GET /v1/users` — список пользователей, только `ADMIN`;
- `PATCH /v1/users/{user_id}/status` — активация/деактивация, только `ADMIN`;
- `GET /health/live` — liveness;
- `GET /health/ready` — readiness с проверкой PostgreSQL.

## Запуск

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Либо production-подобный запуск:

```bash
docker compose up --build
```

Миграции выполняются отдельным одноразовым контейнером до старта API. Приложение не вызывает
`create_all`.

## Проверки

```bash
uv run ruff check app tests alembic
uv run mypy app
uv run pytest tests/unit -q
uv run pytest tests/integration tests/e2e -q  # нужен Docker
```

## Переменные окружения

Все настройки имеют префикс `APP_CONFIG__`; полный пример находится в `.env.example`.
`APP_CONFIG__ADMIN_TELEGRAM_IDS` — JSON-массив Telegram ID, которым при первой регистрации
назначается глобальная роль `ADMIN`. Существующая роль автоматически не повышается.

Секреты, токены, пароли и Telegram initData не должны попадать в логи или Git.
