class AppException(Exception):
    """Базовое доменное исключение приложения."""

    def __init__(self, message: str = "Application error") -> None:
        self.message = message
        super().__init__(message)


class NotFoundException(AppException):
    """Сущность не найдена (ожидается BaseRepository)."""

    def __init__(self, message: str = "Not found") -> None:
        super().__init__(message)
