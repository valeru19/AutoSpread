# backend/alembic/versions

Файлы ревизий Alembic (одна цепочка `down_revision`).

## Содержимое

| Файл | Описание |
| --- | --- |
| [ae4cb034c1ae_0001_initial_schema.py](ae4cb034c1ae_0001_initial_schema.py) | Начальная схема: 17 таблиц, индексы, CHECK, составные FK, `forbid_mutation` на 5 таблицах |
| [b2e8f1a90c4d_0002_append_only_receipt_chat.py](b2e8f1a90c4d_0002_append_only_receipt_chat.py) | Триггеры append-only на `receipt` и `chat_message` |

Append-only (UPDATE/DELETE запрещены триггером):  
`ledger_entry`, `audit_event`, `operator_action`, `config_version`, `ad_snapshot`, `receipt`, `chat_message`.
