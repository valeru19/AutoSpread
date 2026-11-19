from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin

_OPS = (
    "list_ads",
    "create_order",
    "get_order",
    "mark_paid",
    "release",
    "cancel",
    "get_balances",
    "chat_send",
    "chat_list",
)


class ExchangeCall(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    """Идемпотентные вызовы Bybit: запись до и после внешнего действия."""

    __tablename__ = "exchange_call"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_exchange_call_idempotency_key"),
        CheckConstraint(
            "operation IN (" + ", ".join(f"'{o}'" for o in _OPS) + ")",
            name="operation",
        ),
        CheckConstraint(
            "status IN ('started', 'succeeded', 'failed', 'unknown')",
            name="status",
        ),
    )

    exchange_account_id: Mapped[int] = mapped_column(
        ForeignKey("exchange_account.id", ondelete="RESTRICT", name="fk_exchange_call_exchange_account_id"),
        nullable=False,
    )
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("deal.id", ondelete="RESTRICT", name="fk_exchange_call_deal_id"),
        nullable=True,
    )
    order_leg_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_leg.id", ondelete="RESTRICT", name="fk_exchange_call_order_leg_id"),
        nullable=True,
    )
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    request: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
