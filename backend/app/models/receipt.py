from sqlalchemy import BigInteger, CheckConstraint, ForeignKeyConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin


class Receipt(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    """Метаданные чека-доказательства. Append-only (sha256 не подменяется)."""

    __tablename__ = "receipt"
    __table_args__ = (
        CheckConstraint("side IN ('out', 'in')", name="side"),
        ForeignKeyConstraint(
            ["deal_id"],
            ["deal.id"],
            name="fk_receipt_deal_id",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["payment_id", "deal_id", "side"],
            ["payment.id", "payment.deal_id", "payment.direction"],
            name="fk_receipt_payment_deal_side",
            ondelete="RESTRICT",
        ),
        Index("ix_receipt_sha256", "sha256"),
    )

    deal_id: Mapped[int] = mapped_column(nullable=False)
    payment_id: Mapped[int | None] = mapped_column(nullable=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
