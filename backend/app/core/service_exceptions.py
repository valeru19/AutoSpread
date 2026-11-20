"""Бизнес-исключения сервисов. Наследуют AppException; exceptions.py не меняем."""

from app.core.exceptions import AppException


class AppendOnlyViolation(AppException):
    """Попытка update/delete на append-only сущности."""

    def __init__(self, message: str = "Append-only: mutation forbidden") -> None:
        super().__init__(message)


class ReceiptRequired(AppException):
    """Для шага FSM нужен чек, которого нет в контексте."""

    def __init__(self, message: str = "Receipt required") -> None:
        super().__init__(message)


class InvalidTransitionError(AppException):
    """Недопустимый переход автомата состояний сделки."""

    def __init__(self, message: str = "Invalid FSM transition") -> None:
        super().__init__(message)


class ConcurrentModificationError(AppException):
    """Несовпадение row_version (оптимистичная блокировка)."""

    def __init__(self, message: str = "Concurrent modification") -> None:
        super().__init__(message)


class MarginInputError(AppException):
    """Некорректный вход вызова MarginService (не бизнес-отказ)."""

    def __init__(self, message: str = "Invalid margin input") -> None:
        super().__init__(message)
