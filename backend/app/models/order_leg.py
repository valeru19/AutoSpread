from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IntPrimaryKeyMixin, TimestampMixin
from app.models.types import CRYPTO_NUMERIC, FIAT_NUMERIC, PRICE_NUMERIC


class OrderLeg(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_leg"
    __table_args__ = (
        UniqueConstraint("id", "deal_id", "currency", name="uq_order_leg_id_deal_currency"),
        UniqueConstraint("deal_id", "side", name="uq_order_leg_deal_side"),
        UniqueConstraint("idempotency_key", name="uq_order_leg_idempotency_key"),
        Index(
            "uq_order_leg_account_external_order",
            "exchange_account_id",
            "external_order_id",
            unique=True,
            postgresql_where=text("external_order_id IS NOT NULL"),
        ),
        CheckConstraint("side IN ('buy', 'sell')", name="side"),
        CheckConstraint("currency IN ('RUB', 'EUR', 'USD', 'KZT')", name="currency"),
        CheckConstraint(
            "status IN ('created', 'awaiting_payment', 'paid', 'released', 'cancelled', 'appealed')",
            name="status",
        ),
        ForeignKeyConstraint(
            ["deal_id", "currency"],
            ["deal.id", "deal.currency"],
            name="fk_order_leg_deal_currency",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["exchange_account_id"],
            ["exchange_account.id"],
            name="fk_order_leg_exchange_account_id",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["counterparty_id"],
            ["counterparty.id"],
            name="fk_order_leg_counterparty_id",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["ad_snapshot_id", "currency"],
            ["ad_snapshot.id", "ad_snapshot.currency"],
            name="fk_order_leg_ad_snapshot_currency",
            ondelete="RESTRICT",
        ),
    )

    deal_id: Mapped[int] = mapped_column(nullable=False)
    exchange_account_id: Mapped[int] = mapped_column(nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    external_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount_token: Mapped[Decimal] = mapped_column(CRYPTO_NUMERIC, nullable=False)
    price: Mapped[Decimal] = mapped_column(PRICE_NUMERIC, nullable=False)
    amount_fiat: Mapped[Decimal] = mapped_column(FIAT_NUMERIC, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    counterparty_id: Mapped[int] = mapped_column(nullable=False)
    ad_snapshot_id: Mapped[int | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
