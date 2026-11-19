# backend/scripts

Операционные скрипты бэкенда (не часть runtime API).

## Содержимое

| Файл | Описание |
| --- | --- |
| [seed_config_version.py](seed_config_version.py) | Создаёт `config_version` v1 (`require_ack`, лимиты, TTL), если ещё нет |
| [__init__.py](__init__.py) | Пакет для `python -m scripts.…` |

```bash
cd backend
poetry run python -m scripts.seed_config_version
```
