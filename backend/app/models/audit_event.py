from sqlalchemy import CheckConstraint, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin


class AuditEvent(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "audit_event"
    __table_args__ = (
        CheckConstraint("actor_type IN ('system', 'operator', 'agent')", name="actor_type"),
        CheckConstraint(
            "entity_type IN ("
            "'deal', 'order_leg', 'payment', 'opportunity', "
            "'config_version', 'exchange_call', 'receipt', 'other'"
            ")",
            name="entity_type",
        ),
        Index("ix_audit_event_entity", "entity_type", "entity_id"),
        Index("ix_audit_event_created_at", "created_at"),
    )

    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Полиморфная ссылка без FK; int id сущностей (каркасный PK). NULL допустим.
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    input: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
