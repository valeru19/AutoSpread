from app.models.exchange_account import ExchangeAccount
from app.repositories.base_repository import BaseRepository


class ExchangeAccountRepository(BaseRepository[ExchangeAccount]):
    """Репозиторий биржевых аккаунтов."""

    def __init__(self) -> None:
        super().__init__(ExchangeAccount)


exchange_account_repository = ExchangeAccountRepository()
