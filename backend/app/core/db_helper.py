from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


class DatabaseHelper:
    """Engine и фабрика сессий для async SQLAlchemy (используется в core.database)."""

    def __init__(self) -> None:
        self.engine: AsyncEngine = create_async_engine(
            settings.db.url,
            echo=settings.db.echo,
            pool_pre_ping=True,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        await self.engine.dispose()


db_helper = DatabaseHelper()
