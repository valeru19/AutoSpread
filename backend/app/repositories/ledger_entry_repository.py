from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_exceptions import AppendOnlyViolation
from app.models.ledger_entry import LedgerEntry
from app.repositories.base_repository import BaseRepository


class LedgerEntryRepository(BaseRepository[LedgerEntry]):
    """Проводки леджера. Append-only."""

    def __init__(self) -> None:
        super().__init__(LedgerEntry)

    async def update(
        self, session: AsyncSession, primary_key: int, **kwargs: Any
    ) -> LedgerEntry | None:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("ledger_entry is append-only")

    async def delete(self, session: AsyncSession, primary_key: int) -> bool:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("ledger_entry is append-only")


ledger_entry_repository = LedgerEntryRepository()
