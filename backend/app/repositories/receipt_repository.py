from app.models.receipt import Receipt
from app.repositories.base_repository import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    """Репозиторий метаданных чеков."""

    def __init__(self) -> None:
        super().__init__(Receipt)


receipt_repository = ReceiptRepository()
