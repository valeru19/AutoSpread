from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_call import ExchangeCall
from app.repositories.base_repository import BaseRepository


class ExchangeCallRepository(BaseRepository[ExchangeCall]):
    """Репозиторий вызовов биржи."""

    def __init__(self) -> None:
        super().__init__(ExchangeCall)

    async def list_unfinished(self, session: AsyncSession) -> list[ExchangeCall]:
        """
        Незавершённые вызовы (started / unknown).

        :param session: сессия БД
        """
        stmt = select(ExchangeCall).where(
            ExchangeCall.status.in_(("started", "unknown"))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


exchange_call_repository = ExchangeCallRepository()
