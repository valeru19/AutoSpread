from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin
from app.models.types import CRYPTO_NUMERIC, FIAT_NUMERIC, PRICE_NUMERIC


class AdSnapshot(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    """Срез объявления. Append-only. Партиционирование не делаем; срок хранения — в конфиге."""

    __tablename__ = "ad_snapshot"
    __table_args__ = (
        UniqueConstraint("id", "currency", name="uq_ad_snapshot_id_currency"),
        CheckConstraint("token IN ('USDT')", name="token"),
        CheckConstraint("currency IN ('RUB', 'EUR', 'USD', 'KZT')", name="currency"),
        CheckConstraint("side IN ('buy', 'sell')", name="side"),
        # TTL хранения срезов — в конфиге (ADS_TTL_DAYS), не в схеме.
        Index("ix_ad_snapshot_currency_side_captured_at", "currency", "side", "captured_at"),
        Index("ix_ad_snapshot_external_ad_id", "external_ad_id"),
        Index("ix_ad_snapshot_counterparty_id", "counterparty_id"),
    )

    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    external_ad_id: Mapped[str] = mapped_column(String(128), nullable=False)
    token: Mapped[str] = mapped_column(String(16), nullable=False, server_default="USDT")
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    price: Mapped[Decimal] = mapped_column(PRICE_NUMERIC, nullable=False)
    available_amount: Mapped[Decimal] = mapped_column(CRYPTO_NUMERIC, nullable=False)
    min_amount: Mapped[Decimal] = mapped_column(FIAT_NUMERIC, nullable=False)
    max_amount: Mapped[Decimal] = mapped_column(FIAT_NUMERIC, nullable=False)
    payment_methods: Mapped[dict | list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    counterparty_id: Mapped[int] = mapped_column(
        ForeignKey("counterparty.id", ondelete="RESTRICT", name="fk_ad_snapshot_counterparty_id"),
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
