from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin


class AgentProposal(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "agent_proposal"
    __table_args__ = (
        CheckConstraint("agent_role IN ('analyst', 'advisor', 'executor')", name="agent_role"),
        CheckConstraint("status IN ('proposed', 'accepted', 'rejected')", name="status"),
    )

    agent_role: Mapped[str] = mapped_column(String(32), nullable=False)
    proposal: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="proposed")
    decided_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
