# backend/app/core

Инфраструктурное ядро приложения: настройки, ORM-база, доступ к БД, исключения.

## Содержимое

| Файл | Назначение |
| --- | --- |
| [config.py](config.py) | `Settings` / `DbSettings` из `.env` (pydantic-settings + dotenv). **Не менять без нужды** — каркасный файл. |
| [base.py](base.py) | `Base` (DeclarativeBase + naming_convention), `IntPrimaryKeyMixin`, `TimestampMixin`, `CreatedAtMixin` |
| [db_helper.py](db_helper.py) | `DatabaseHelper`: async engine (asyncpg) и `async_sessionmaker` |
| [database.py](database.py) | Генераторы сессий `get_session` / `get_readonly_session` для Dishka/UoW |
| [exceptions.py](exceptions.py) | `AppException`, `NotFoundException` (ожидается `BaseRepository`) |

## Заметки

- Приложение → `postgresql+asyncpg://…`  
- Alembic → тот же URL, в `alembic/env.py` переписывается на `postgresql+psycopg://`  
- Изменяемые таблицы: `TimestampMixin` (`created_at` + `updated_at`)  
- Append-only: только `CreatedAtMixin` (`created_at`); мутации режет триггер в БД  
