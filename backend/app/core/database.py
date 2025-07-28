"""
Database configuration and connection management
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from typing import AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    future=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Metadata for migrations
metadata = MetaData()


class Base(DeclarativeBase):
    """Base class for all database models"""
    metadata = metadata


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection and verify connectivity
    """
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Test connection with proper text() wrapper
            await conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection established successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections
    """
    await engine.dispose()
    logger.info("🔒 Database connections closed")
