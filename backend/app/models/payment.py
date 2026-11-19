from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IntPrimaryKeyMixin, TimestampMixin
from app.models.types import FIAT_NUMERIC


class Payment(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment"
    __table_args__ = (
        UniqueConstraint("id", "deal_id", name="uq_payment_id_deal"),
        UniqueConstraint("id", "deal_id", "direction", name="uq_payment_id_deal_direction"),
        CheckConstraint("direction IN ('in', 'out')", name="direction"),
        CheckConstraint("currency IN ('RUB', 'EUR', 'USD', 'KZT')", name="currency"),
        CheckConstraint(
            "status IN ('pending', 'sent', 'matched', 'failed', 'cancelled')",
            name="status",
        ),
        ForeignKeyConstraint(
            ["deal_id"],
            ["deal.id"],
            name="fk_payment_deal_id",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["order_leg_id", "deal_id", "currency"],
            ["order_leg.id", "order_leg.deal_id", "order_leg.currency"],
            name="fk_payment_order_leg_deal_currency",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["payment_instrument_id", "currency"],
            ["payment_instrument.id", "payment_instrument.currency"],
            name="fk_payment_instrument_currency",
            ondelete="RESTRICT",
        ),
    )

    deal_id: Mapped[int] = mapped_column(nullable=False)
    order_leg_id: Mapped[int] = mapped_column(nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(FIAT_NUMERIC, nullable=False)
    payment_instrument_id: Mapped[int | None] = mapped_column(nullable=True)
    counterparty_requisites_masked: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    operator_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
