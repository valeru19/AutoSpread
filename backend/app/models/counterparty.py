from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IntPrimaryKeyMixin, TimestampMixin


class Counterparty(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "counterparty"
    __table_args__ = (
        UniqueConstraint("exchange", "external_id", name="uq_counterparty_exchange_external_id"),
    )

    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(256), nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    orders_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blacklist_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
