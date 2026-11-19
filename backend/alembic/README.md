# backend/alembic

Миграции PostgreSQL через Alembic. Драйвер миграций — **sync psycopg**; URL берётся из `app.core.config.settings` и в [env.py](env.py) переписывается `asyncpg` → `psycopg`.

## Содержимое

| Путь | Описание |
| --- | --- |
| [env.py](env.py) | Online/offline миграции, `target_metadata = Base.metadata`, импорт `app.models` |
| [versions/](versions/) | Ревизии схемы |
| [script.py.mako](script.py.mako) | Шаблон новой ревизии |

## Команды

Из каталога `backend/`:

```bash
poetry run alembic upgrade head
poetry run alembic downgrade base
poetry run alembic check
poetry run alembic revision --autogenerate -m "short_name"
```
