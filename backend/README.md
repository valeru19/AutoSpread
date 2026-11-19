# backend

Серверная часть AutoSpread: FastAPI, Telegram-бот, воркеры, PostgreSQL.  
DI — **Dishka**, зависимости — **Poetry**, Python **≥3.12,<3.14**.

## Содержимое

| Путь | Описание |
| --- | --- |
| [app/](app/) | Исходный код приложения |
| [alembic/](alembic/) | Миграции схемы БД |
| [tests/](tests/) | Pytest: схема, ограничения, append-only |
| [scripts/](scripts/) | Утилиты (seed конфига и т.п.) |
| [alembic.ini](alembic.ini) | Конфиг Alembic |
| [pyproject.toml](pyproject.toml) | Метаданные и зависимости Poetry |
| [.env.example](.env.example) | Пример переменных окружения |
| [.gitignore](.gitignore) | Исключения для git |

## Установка

```bash
cd backend
poetry env use 3.12
poetry install
```

Локальный Postgres/Redis: из корня репозитория `docker compose up -d`.  
На Windows, если занят порт **5432**, используется override на **5433** (см. `docker-compose.override.yml` и `.env`).

```bash
poetry run alembic upgrade head
poetry run python -m scripts.seed_config_version
poetry run pytest
```

Запуск API (когда появится `app.api.main`):

```bash
poetry run uvicorn app.api.main:app --reload
```

## Статус

- ✅ ORM-модели, миграция `0001_initial_schema`, триггеры append-only, тесты схемы  
- ⏳ HTTP API, бот, сервисы, репозитории домена, воркеры Bybit — ещё не реализованы  
