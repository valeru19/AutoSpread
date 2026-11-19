from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_exceptions import AppendOnlyViolation
from app.models.operator_action import OperatorAction
from app.repositories.base_repository import BaseRepository


class OperatorActionRepository(BaseRepository[OperatorAction]):
    """Действия оператора. Append-only."""

    def __init__(self) -> None:
        super().__init__(OperatorAction)

    async def update(
        self, session: AsyncSession, primary_key: int, **kwargs: Any
    ) -> OperatorAction | None:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("operator_action is append-only")

    async def delete(self, session: AsyncSession, primary_key: int) -> bool:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("operator_action is append-only")


operator_action_repository = OperatorActionRepository()
