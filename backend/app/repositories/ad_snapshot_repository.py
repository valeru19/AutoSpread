from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_exceptions import AppendOnlyViolation
from app.models.ad_snapshot import AdSnapshot
from app.repositories.base_repository import BaseRepository


class AdSnapshotRepository(BaseRepository[AdSnapshot]):
    """Срезы объявлений. Append-only: update/delete запрещены."""

    def __init__(self) -> None:
        super().__init__(AdSnapshot)

    async def list_latest(
        self,
        session: AsyncSession,
        currency: str,
        side: str,
        *,
        limit: int = 100,
    ) -> list[AdSnapshot]:
        """
        Последние срезы по валюте и стороне.

        :param session: сессия БД
        :param currency: фиат-валюта
        :param side: сторона рекламодателя
        :param limit: максимум строк
        """
        stmt = (
            select(AdSnapshot)
            .where(AdSnapshot.currency == currency, AdSnapshot.side == side)
            .order_by(AdSnapshot.captured_at.desc(), AdSnapshot.id.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, session: AsyncSession, primary_key: int, **kwargs: Any
    ) -> AdSnapshot | None:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("ad_snapshot is append-only")

    async def delete(self, session: AsyncSession, primary_key: int) -> bool:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("ad_snapshot is append-only")


ad_snapshot_repository = AdSnapshotRepository()
