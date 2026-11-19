from app.models.balance_snapshot import BalanceSnapshot
from app.repositories.base_repository import BaseRepository


class BalanceSnapshotRepository(BaseRepository[BalanceSnapshot]):
    """Репозиторий срезов балансов."""

    def __init__(self) -> None:
        super().__init__(BalanceSnapshot)


balance_snapshot_repository = BalanceSnapshotRepository()
