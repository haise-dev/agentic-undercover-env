from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings

# Create async engine
# SQL_ECHO determines if SQL queries are printed to stdout
async_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    future=True,
)

# Async session factory
AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI-compatible async dependency that yields a database session.
    Commits on success, rolls back on exception, always closes.

    Usage (FastAPI):
        async def my_endpoint(session: AsyncSession = Depends(get_session)):
            ...

    Usage (direct):
        from contextlib import asynccontextmanager
        async with asynccontextmanager(get_session)() as session:
            result = await session.execute(...)
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all_tables() -> None:
    """
    Creates all tables from ORM metadata. Used in tests only.
    Production uses Alembic migrations.
    """
    from src.db.models import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """
    Drops all tables from ORM metadata. Used in tests only.
    """
    from src.db.models import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
