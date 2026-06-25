from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from backend.config import settings

# Create async engine. Uses DATABASE_URL from global settings.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    """
    Base class for declarative models.
    """
    pass

async def get_db_session():
    """
    Dependency helper to acquire database sessions asynchronously.
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

# INTEGRATION NOTE
# Member 4 (API) uses get_db_session to inject connections to routes.
# Make sure to run DB migrations before initiating pipeline runs.
