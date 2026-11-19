from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_leg import OrderLeg
from app.repositories.base_repository import BaseRepository


class OrderLegRepository(BaseRepository[OrderLeg]):
    """Репозиторий ног ордеров."""

    def __init__(self) -> None:
        super().__init__(OrderLeg)

    async def list_by_deal(self, session: AsyncSession, deal_id: int) -> list[OrderLeg]:
        """
        Ноги сделки.

        :param session: сессия БД
        :param deal_id: id сделки
        """
        return await self.find_many_by_field(session, "deal_id", deal_id)


order_leg_repository = OrderLegRepository()
