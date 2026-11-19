from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IntPrimaryKeyMixin, TimestampMixin
from app.models.types import CRYPTO_NUMERIC, FIAT_NUMERIC, PCT_NUMERIC, PRICE_NUMERIC


class Opportunity(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "opportunity"
    __table_args__ = (
        UniqueConstraint("id", "currency", name="uq_opportunity_id_currency"),
        CheckConstraint("currency IN ('RUB', 'EUR', 'USD', 'KZT')", name="currency"),
        CheckConstraint("decision IN ('taken', 'skipped', 'expired')", name="decision"),
        CheckConstraint("buy_ad_snapshot_id <> sell_ad_snapshot_id", name="buy_ne_sell"),
        ForeignKeyConstraint(
            ["buy_ad_snapshot_id", "currency"],
            ["ad_snapshot.id", "ad_snapshot.currency"],
            name="fk_opportunity_buy_ad_snapshot_currency",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["sell_ad_snapshot_id", "currency"],
            ["ad_snapshot.id", "ad_snapshot.currency"],
            name="fk_opportunity_sell_ad_snapshot_currency",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["config_version_id"],
            ["config_version.id"],
            name="fk_opportunity_config_version_id",
            ondelete="RESTRICT",
        ),
    )

    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    buy_ad_snapshot_id: Mapped[int] = mapped_column(nullable=False)
    sell_ad_snapshot_id: Mapped[int] = mapped_column(nullable=False)
    amount_token: Mapped[Decimal] = mapped_column(CRYPTO_NUMERIC, nullable=False)
    buy_price: Mapped[Decimal] = mapped_column(PRICE_NUMERIC, nullable=False)
    sell_price: Mapped[Decimal] = mapped_column(PRICE_NUMERIC, nullable=False)
    gross_margin_pct: Mapped[Decimal] = mapped_column(PCT_NUMERIC, nullable=False)
    net_margin_pct: Mapped[Decimal] = mapped_column(PCT_NUMERIC, nullable=False)
    net_profit_fiat: Mapped[Decimal] = mapped_column(FIAT_NUMERIC, nullable=False)
    fees: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    calc_inputs: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    config_version_id: Mapped[int] = mapped_column(nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
