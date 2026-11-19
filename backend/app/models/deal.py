from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IntPrimaryKeyMixin, TimestampMixin
from app.models.types import CRYPTO_NUMERIC, FIAT_NUMERIC, PCT_NUMERIC

_DEAL_STATES = (
    "opportunity",
    "awaiting_open_ack",
    "buy_order",
    "awaiting_pay_ack",
    "mark_paid",
    "awaiting_crypto",
    "sell_order",
    "awaiting_incoming",
    "awaiting_release_ack",
    "released",
    "closed",
    "cancelled",
    "dispute",
)


class Deal(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deal"
    __table_args__ = (
        UniqueConstraint("id", "currency", name="uq_deal_id_currency"),
        UniqueConstraint("opportunity_id", name="uq_deal_opportunity_id"),
        CheckConstraint("currency IN ('RUB', 'EUR', 'USD', 'KZT')", name="currency"),
        CheckConstraint(
            "state IN (" + ", ".join(f"'{s}'" for s in _DEAL_STATES) + ")",
            name="state",
        ),
        CheckConstraint(
            "mode IN ('dry_run', 'paper', 'live_confirm', 'live')",
            name="mode",
        ),
        ForeignKeyConstraint(
            ["opportunity_id", "currency"],
            ["opportunity.id", "opportunity.currency"],
            name="fk_deal_opportunity_currency",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["config_version_id"],
            ["config_version.id"],
            name="fk_deal_config_version_id",
            ondelete="RESTRICT",
        ),
        Index("ix_deal_state", "state"),
        Index(
            "ix_deal_open_states",
            "state",
            postgresql_where=text("state NOT IN ('closed', 'cancelled')"),
        ),
    )

    opportunity_id: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_token: Mapped[Decimal] = mapped_column(CRYPTO_NUMERIC, nullable=False)
    planned_margin_pct: Mapped[Decimal] = mapped_column(PCT_NUMERIC, nullable=False)
    planned_profit_fiat: Mapped[Decimal] = mapped_column(FIAT_NUMERIC, nullable=False)
    actual_profit_fiat: Mapped[Decimal | None] = mapped_column(FIAT_NUMERIC, nullable=True)
    config_version_id: Mapped[int] = mapped_column(nullable=False)
    state_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
