# SchoolHub Auth Service

Сервис идентификации пользователей SchoolHub. Он хранит связь между Telegram-пользователем и
глобальной ролью (`admin`/`user`), выдаёт профиль текущего пользователя и позволяет администратору
включать или отключать аккаунты.

## Архитектура

```text
HTTP API -> Auth/User Service -> User Repository -> PostgreSQL
                     -> Telegram initData HMAC verification
                     -> JWT access/refresh tokens
```

Telegram `initData` проверяется по алгоритму Telegram Mini Apps с контролем срока жизни. JWT
проверяются по подписи, issuer, audience, типу и сроку действия. Refresh-токены ротируются,
хранятся в PostgreSQL в виде SHA-256 hash; повторное использование отозванного токена отзывает
всю пользовательскую сессию.

## API

- `POST /v1/auth/telegram` — проверка Telegram initData, регистрация/обновление профиля, выдача токенов;
- `POST /v1/auth/refresh` — одноразовая ротация refresh-токена;
- `POST /v1/auth/logout` — отзыв текущего refresh-токена;
- `GET /v1/auth/verify` — внутренняя проверка access token для API Gateway;
- `GET /v1/users/me` — профиль текущего пользователя;
- `GET /v1/users` — список пользователей, только `admin`;
- `GET /v1/users/resolve?username=@name` — поиск активного пользователя по Telegram username, только `admin`;
- `PATCH /v1/users/{user_id}/status` — активация/деактивация, только `admin`;
- `GET /health/live` — liveness;
- `GET /health/ready` — readiness с проверкой PostgreSQL.
- `GET /metrics` — Prometheus metrics.

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
uv run python -m pytest tests/unit -q
uv run python -m pytest tests/integration tests/e2e -q  # нужен Docker
```

## Переменные окружения

Все настройки имеют префикс `APP_CONFIG__`; полный пример находится в `.env.example`.
`APP_CONFIG__ADMIN_TELEGRAM_IDS` — JSON-массив Telegram ID, которым при первой регистрации
назначается глобальная роль `admin`. Существующая роль автоматически не повышается.

Секреты, токены, пароли и Telegram initData не должны попадать в логи или Git.

Полный запуск всех компонентов описан в репозитории
[School Service](https://github.com/polnyiLox/schoolhub-school-service#полное-развертывание-schoolhub).
