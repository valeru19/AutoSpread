# backend/app

Пакет приложения AutoSpread (`import app...`).

## Содержимое

| Папка | Описание | Статус |
| --- | --- | --- |
| [core/](core/) | Конфиг, Base/миксины, сессии БД, исключения | есть код |
| [models/](models/) | SQLAlchemy 2 ORM, 17 таблиц + enums/types | есть код |
| [repositories/](repositories/) | Доступ к БД; пока только `BaseRepository` | каркас |
| [api/](api/) | FastAPI: роуты, DTO, сервисы | каркас (без `main.py`) |
| [bot/](bot/) | Telegram-бот (aiogram) | пусто |

Бизнес-логика (FSM сделок, маржа, Bybit) сюда ещё не вынесена — следующий этап после репозиториев.
