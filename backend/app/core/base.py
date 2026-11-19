import re
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Явные имена ограничений: Base менять для naming_convention можно (разрешено для миксинов/Base).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(self) -> str:
        # Единообразно строим snake_case имена таблиц и множественное число в одном месте.
        # Для доменных таблиц ТЗ задаём __tablename__ явно (singular).
        table_name = re.sub(r"(?<!^)(?=[A-Z])", "_", self.__name__).lower()
        if table_name.endswith("analysis"):
            return f"{table_name[:-2]}es"
        if table_name.endswith("y"):
            return f"{table_name[:-1]}ies"
        return f"{table_name}s"


class IntPrimaryKeyMixin:
    """Суррогатный int PK. Атрибут id — для совместимости с BaseRepository."""

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        sort_order=-10,
    )


class TimestampMixin:
    """Изменяемые таблицы: created_at + updated_at (timestamptz / UTC)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtMixin:
    """Append-only таблицы: только created_at."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
