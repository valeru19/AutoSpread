# backend/app/models

SQLAlchemy 2 ORM-модели домена AutoSpread. Имена таблиц — **singular**. PK — **int** (совместимость с `BaseRepository`). Деньги — `Numeric`, не `float`. Enum-значения в БД — `VARCHAR` + `CHECK`, не native PG ENUM.

## Содержимое

| Файл | Таблица / роль |
| --- | --- |
| [enums.py](enums.py) | Строковые enum’ы для кода (не типы колонок БД) |
| [types.py](types.py) | `CRYPTO_NUMERIC(38,18)`, `FIAT(24,4)`, `PRICE(24,8)`, `PCT(12,6)` |
| [exchange_account.py](exchange_account.py) | Счёт биржи; CHECK: нет `withdraw=true` |
| [counterparty.py](counterparty.py) | Контрагент P2P |
| [ad_snapshot.py](ad_snapshot.py) | Срез объявления (**append-only**) |
| [config_version.py](config_version.py) | Неизменяемая версия конфига (**append-only**) |
| [opportunity.py](opportunity.py) | Рассчитанная связка buy/sell |
| [payment_instrument.py](payment_instrument.py) | Карта/метод оплаты оператора |
| [deal.py](deal.py) | Сделка / FSM-состояние |
| [order_leg.py](order_leg.py) | Нога ордера (buy/sell) |
| [payment.py](payment.py) | Платёж in/out |
| [receipt.py](receipt.py) | Метаданные чека (файл вне БД; **append-only**) |
| [chat_message.py](chat_message.py) | Сообщение чата P2P (`message_text` → колонка `text`; **append-only**) |
| [operator_action.py](operator_action.py) | Ack/reject оператора (**append-only**) |
| [balance_snapshot.py](balance_snapshot.py) | Срез балансов |
| [ledger_entry.py](ledger_entry.py) | Двойная запись (**append-only**) |
| [audit_event.py](audit_event.py) | Аудит (**append-only**) |
| [agent_proposal.py](agent_proposal.py) | Задел под ИИ-агентов |
| [exchange_call.py](exchange_call.py) | Идемпотентные вызовы Bybit |
| [__init__.py](__init__.py) | Экспорт моделей для Alembic metadata |

## Составные FK (C1–C7)

Согласованность валюты/сделки/платежа через composite FK (см. миграцию и ТЗ).  
TTL хранения `ad_snapshot` / `receipt` — в env (`ADS_TTL_DAYS`, `RECEIPT_TTL_DAYS`), не в схеме.

Подробно (зачем / связи / сценарии): [zdocs/db/сущности.md](../../../zdocs/db/сущности.md).
