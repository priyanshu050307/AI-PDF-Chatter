from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import settings

from sqlalchemy import event

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_kwargs = {"echo": settings.DEBUG, "future": True}
if is_sqlite:
    # NullPool: each async request gets a fresh connection.
    # This eliminates SQLite "database is locked" errors that occur when
    # concurrent requests (e.g. progress save + chat message) share a
    # connection from the same pool and deadlock on the WAL write lock.
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": 60.0,  # sqlite3 driver-level lock wait (seconds)
    }
else:
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        # In aiosqlite, dbapi_connection is AsyncAdapt_aiosqlite_connection.
        # Access the underlying raw sqlite3.Connection via _connection._conn
        raw_conn = getattr(dbapi_connection, "_connection", dbapi_connection)
        sqlite3_conn = getattr(raw_conn, "_conn", raw_conn)
        try:
            cursor = sqlite3_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=60000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()
        except Exception:
            pass

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Base ORM model class"""
    pass


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency helper to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            if session.is_active:
                await session.commit()
        except Exception:
            if session.is_active:
                await session.rollback()
            raise
        finally:
            await session.close()

