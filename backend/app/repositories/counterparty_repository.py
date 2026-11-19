from app.models.counterparty import Counterparty
from app.repositories.base_repository import BaseRepository


class CounterpartyRepository(BaseRepository[Counterparty]):
    """Репозиторий контрагентов P2P."""

    def __init__(self) -> None:
        super().__init__(Counterparty)


counterparty_repository = CounterpartyRepository()
