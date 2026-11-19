import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin
from app.models.types import CRYPTO_NUMERIC


class LedgerEntry(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ledger_entry"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "(payment_id IS NULL) OR (deal_id IS NOT NULL)",
            name="payment_implies_deal",
        ),
        ForeignKeyConstraint(
            ["deal_id"],
            ["deal.id"],
            name="fk_ledger_entry_deal_id",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["payment_id", "deal_id"],
            ["payment.id", "payment.deal_id"],
            name="fk_ledger_entry_payment_deal",
            ondelete="RESTRICT",
        ),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    debit_account: Mapped[str] = mapped_column(String(128), nullable=False)
    credit_account: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[Decimal] = mapped_column(CRYPTO_NUMERIC, nullable=False)
    asset: Mapped[str] = mapped_column(String(32), nullable=False)
    deal_id: Mapped[int | None] = mapped_column(nullable=True)
    payment_id: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
