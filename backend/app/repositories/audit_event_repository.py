from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.service_exceptions import AppendOnlyViolation
from app.models.audit_event import AuditEvent
from app.repositories.base_repository import BaseRepository


class AuditEventRepository(BaseRepository[AuditEvent]):
    """Аудит-события. Append-only."""

    def __init__(self) -> None:
        super().__init__(AuditEvent)

    async def update(
        self, session: AsyncSession, primary_key: int, **kwargs: Any
    ) -> AuditEvent | None:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("audit_event is append-only")

    async def delete(self, session: AsyncSession, primary_key: int) -> bool:
        """Запрещено (append-only)."""
        raise AppendOnlyViolation("audit_event is append-only")


audit_event_repository = AuditEventRepository()
