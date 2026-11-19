from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin


class ChatMessage(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    """Сообщение P2P-чата. Append-only: спорную переписку не редактируем."""

    __tablename__ = "chat_message"
    __table_args__ = (
        CheckConstraint("direction IN ('in', 'out', 'system')", name="direction"),
        Index(
            "uq_chat_message_leg_external",
            "order_leg_id",
            "external_message_id",
            unique=True,
            postgresql_where=sa_text("external_message_id IS NOT NULL"),
        ),
    )

    order_leg_id: Mapped[int] = mapped_column(
        ForeignKey("order_leg.id", ondelete="RESTRICT", name="fk_chat_message_order_leg_id"),
        nullable=False,
    )
    external_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    # Колонка БД `text`; атрибут message_text — чтобы не затенять sqlalchemy.text
    message_text: Mapped[str | None] = mapped_column("text", Text, nullable=True)
    attachment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"))
