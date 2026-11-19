from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_exceptions import AppendOnlyViolation
from app.models.config_version import ConfigVersion
from app.repositories.base_repository import BaseRepository


class ConfigVersionRepository(BaseRepository[ConfigVersion]):
    """Версии конфига. Append-only. Активна max(version)."""

    def __init__(self) -> None:
        super().__init__(ConfigVersion)

    async def get_active(self, session: AsyncSession) -> ConfigVersion | None:
        """
        Активная версия — с максимальным version.

        :param session: сессия БД
        """
        stmt = (
            select(ConfigVersion)
            .order_by(ConfigVersion.version.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, primary_key: int, **kwargs: Any
    ) -> ConfigVersion | None:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("config_version is append-only")

    async def delete(self, session: AsyncSession, primary_key: int) -> bool:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("config_version is append-only")


config_version_repository = ConfigVersionRepository()
