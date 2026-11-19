# Docker

Локальная инфраструктура AutoSpread через Docker Compose.

## Сервисы

| Сервис | Образ | Порт на хосте | Назначение |
| --- | --- | --- | --- |
| `postgres` | `postgres:16` | `5432` (локально часто `5433` через `docker-compose.override.yml`) | БД сделок, ledger, audit |
| `redis` | `redis:7` | `6379` | очередь arq, locks, кэш |

Том `autospread_files` зарезервирован под чеки (подключится к api/worker позже).

## Запуск

Из корня репозитория:

```bash
docker compose up -d
docker compose ps
docker compose logs -f postgres redis
```

## redis-cli

Сервер Redis — в Docker. Клиент:

```bash
# из корня репозитория
scripts\redis-cli.cmd ping
scripts\redis-cli.cmd keys *

# или напрямую
docker compose exec redis redis-cli
```

Нативный Windows `redis-cli` не обязателен. При желании: `winget install Redis.Redis` (старый порт Redis под Windows).

Остановка:

```bash
docker compose down
```

Данные БД/Redis сохраняются в named volumes (не удаляются при `down`). Сброс данных:

```bash
docker compose down -v
```

## Связь с `.env`

В `backend/.env` (скопируйте из `.env.example`):

```env
DATABASE_URL=postgresql+asyncpg://autospread:autospread@localhost:5432/autospread
REDIS_URL=redis://localhost:6379/0
```

## Конфликт с локальным PostgreSQL Windows

Если служба `postgresql-x64-16` уже слушает `5432`, либо остановите её, либо в `docker-compose.yml` смените проброс на `"5433:5432"` и обновите `DATABASE_URL` (порт `5433`).
