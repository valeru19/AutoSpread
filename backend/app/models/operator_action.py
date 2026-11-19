from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin


class OperatorAction(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "operator_action"
    __table_args__ = (
        CheckConstraint(
            "step IN ('open', 'pay', 'mark_paid', 'release', 'cancel', 'payment_matched')",
            name="step",
        ),
        CheckConstraint("action IN ('ack', 'reject')", name="action"),
    )

    deal_id: Mapped[int] = mapped_column(
        ForeignKey("deal.id", ondelete="RESTRICT", name="fk_operator_action_deal_id"),
        nullable=False,
    )
    step: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
