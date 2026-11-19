from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Репозиторий платежей."""

    def __init__(self) -> None:
        super().__init__(Payment)

    async def list_by_deal(self, session: AsyncSession, deal_id: int) -> list[Payment]:
        """
        Платежи сделки.

        :param session: сессия БД
        :param deal_id: id сделки
        """
        return await self.find_many_by_field(session, "deal_id", deal_id)


payment_repository = PaymentRepository()
