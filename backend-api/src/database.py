import contextlib

from typing import Any, AsyncIterator

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine.url import make_url
from src.settings import get_settings
from redis.asyncio import Redis

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    AsyncAttrs,
    async_sessionmaker,
    create_async_engine,
)

# Note: DB is async compatible
# Load DATABASE_URL from environment variable
DATABASE_URL = get_settings().SUPABASE_DB_URL

# Base class for all ORM models
class Base(AsyncAttrs, DeclarativeBase):
    pass


class DatabaseSessionManager:
    """
    Manages the async SQLAlchemy engine and session lifecycle.
    Supports both Postgres (e.g., Supabase) and SQLite for testing.
    """

    def __init__(self, db_url: str, engine_kwargs: dict[str, Any] = {}):
        self._url = db_url
        self._engine = None
        self._sessionmaker = None

        # Parse URL and detect DB type (postgres or sqlite)
        url_obj = make_url(db_url)
        is_postgres = url_obj.drivername.startswith("postgresql")

        connect_args = {"sslmode": "require"} if is_postgres else {}

        self._engine = create_async_engine(
            db_url,
            connect_args=connect_args,
            **engine_kwargs,
        )

        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def close(self):
        """Disposes the engine on app shutdown"""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        """Yields a raw database connection"""
        if self._engine is None:
            raise Exception("Database engine is not initialized")

        async with self._engine.begin() as conn:
            try:
                yield conn
            except Exception:
                await conn.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yields an ORM session for use in endpoints or services"""
        if self._sessionmaker is None:
            raise Exception("Sessionmaker is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Read database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Create global session manager instance
sessionmanager = DatabaseSessionManager(DATABASE_URL)


# FastAPI dependency
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Dependency that yields a database session"""
    async with sessionmanager.session() as session:
        yield session


def init_redis():
    return Redis(
        host="redis-13649.crce199.us-west-2-2.ec2.redns.redis-cloud.com",
        port=13649,
        decode_responses=True,
        username="default",
        password=get_settings().REDIS_PASSWORD,
    )