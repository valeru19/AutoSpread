# backend/tests

Pytest + pytest-asyncio. Тесты схемы БД ходят в отдельную БД **`autospread_test`** (создаётся при необходимости).

## Содержимое

| Файл | Что проверяет |
| --- | --- |
| [conftest.py](conftest.py) | Подмена `DATABASE_URL` → `autospread_test`, `alembic upgrade`, сессия с rollback, фикстура `seed_market` |
| [test_alembic.py](test_alembic.py) | upgrade ↔ downgrade, `alembic check`, одна head-ревизия |
| [test_money_precision.py](test_money_precision.py) | Round-trip Decimal crypto 18 / fiat 4 знака |
| [test_constraints.py](test_constraints.py) | CHECK, UNIQUE, FK RESTRICT, составной FK валюты |
| [test_append_only.py](test_append_only.py) | Триггеры forbid_mutation на UPDATE/DELETE |
| [test_partial_index.py](test_partial_index.py) | EXPLAIN использует `ix_deal_open_states` |

```bash
cd backend
poetry run pytest
```
