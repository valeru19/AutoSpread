from sqlalchemy import Boolean, CheckConstraint, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, IntPrimaryKeyMixin, TimestampMixin


class ExchangeAccount(IntPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exchange_account"
    __table_args__ = (
        UniqueConstraint("exchange", "label", name="uq_exchange_account_exchange_label"),
        CheckConstraint("exchange IN ('bybit')", name="exchange"),
        CheckConstraint("mode IN ('dry_run', 'paper', 'live_confirm', 'live')", name="mode"),
        # withdraw не должен быть true в permissions
        CheckConstraint(
            "(permissions ->> 'withdraw') IS DISTINCT FROM 'true'",
            name="permissions_no_withdraw",
        ),
    )

    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    secret_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
