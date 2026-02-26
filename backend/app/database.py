"""
GreenPulse AI — Database Engine & Session Factory
Async SQLAlchemy setup for MySQL.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=(settings.environment == "development"),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency for DB session injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables (used in dev/testing; production uses Alembic)."""
    async with engine.begin() as conn:
        from app.models import location, sensor_reading, alert, compliance, recommendation, agent_log, model_registry  # noqa
        await conn.run_sync(Base.metadata.create_all)
