from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin
from app.models.types import CRYPTO_NUMERIC


class BalanceSnapshot(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "balance_snapshot"
    __table_args__ = (
        CheckConstraint("source IN ('bybit', 'manual_fiat')", name="source"),
        CheckConstraint(
            "(source = 'bybit' AND exchange_account_id IS NOT NULL AND payment_instrument_id IS NULL) "
            "OR (source = 'manual_fiat' AND payment_instrument_id IS NOT NULL AND exchange_account_id IS NULL)",
            name="source_refs",
        ),
    )

    source: Mapped[str] = mapped_column(String(32), nullable=False)
    asset: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(CRYPTO_NUMERIC, nullable=False)
    exchange_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("exchange_account.id", ondelete="RESTRICT", name="fk_balance_snapshot_exchange_account_id"),
        nullable=True,
    )
    payment_instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("payment_instrument.id", ondelete="RESTRICT", name="fk_balance_snapshot_payment_instrument_id"),
        nullable=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
