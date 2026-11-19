from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IntPrimaryKeyMixin, TimestampMixin
from app.models.types import FIAT_NUMERIC


class PaymentInstrument(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_instrument"
    __table_args__ = (
        UniqueConstraint("id", "currency", name="uq_payment_instrument_id_currency"),
        CheckConstraint("currency IN ('RUB', 'EUR', 'USD', 'KZT')", name="currency"),
        Index("ix_payment_instrument_currency_country_active", "currency", "country_code", "is_active"),
    )

    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    method_code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    masked_details: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    per_tx_limit: Mapped[Decimal | None] = mapped_column(FIAT_NUMERIC, nullable=True)
    daily_limit_amount: Mapped[Decimal | None] = mapped_column(FIAT_NUMERIC, nullable=True)
    daily_limit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
