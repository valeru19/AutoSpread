from sqlalchemy import BigInteger, CheckConstraint, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, CreatedAtMixin, IntPrimaryKeyMixin


class ConfigVersion(IntPrimaryKeyMixin, CreatedAtMixin, Base):
    """Неизменяемая версия конфига. Активна версия с максимальным version."""

    __tablename__ = "config_version"
    __table_args__ = (
        UniqueConstraint("version", name="uq_config_version_version"),
        CheckConstraint("version > 0", name="version_positive"),
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
