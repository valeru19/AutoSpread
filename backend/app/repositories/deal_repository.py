from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal
from app.repositories.base_repository import BaseRepository


class DealRepository(BaseRepository[Deal]):
    """Репозиторий сделок."""

    def __init__(self) -> None:
        super().__init__(Deal)

    async def list_open(self, session: AsyncSession) -> list[Deal]:
        """
        Открытые сделки (не closed/cancelled); индекс ix_deal_open_states.

        :param session: сессия БД
        """
        stmt = select(Deal).where(~Deal.state.in_(("closed", "cancelled")))
        result = await session.execute(stmt)
        return list(result.scalars().all())


deal_repository = DealRepository()
