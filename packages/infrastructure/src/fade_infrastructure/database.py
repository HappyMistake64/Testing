"""SQLAlchemy async database setup with SQLite WAL."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from fade_infrastructure.settings import Settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


def _configure_sqlite(engine: AsyncEngine) -> None:
    """Enable WAL mode and foreign keys for SQLite connections."""

    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_conn, _connection_record) -> None:  # type: ignore[no-untyped-def]
        if engine.dialect.name == "sqlite":
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


def create_engine(settings: Settings) -> AsyncEngine:
    """Create async SQLAlchemy engine."""
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
    )
    _configure_sqlite(engine)
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_database_health(session: AsyncSession) -> dict[str, object]:
    """Run database health checks."""
    result: dict[str, object] = {
        "connected": False,
        "wal_mode": None,
        "integrity_ok": None,
        "project_count": None,
    }

    try:
        await session.execute(text("SELECT 1"))
        result["connected"] = True

        journal = await session.execute(text("PRAGMA journal_mode"))
        wal_row = journal.scalar_one()
        result["wal_mode"] = str(wal_row).lower() == "wal"

        integrity = await session.execute(text("PRAGMA integrity_check"))
        integrity_val = integrity.scalar_one()
        result["integrity_ok"] = integrity_val == "ok"

        count_result = await session.execute(text("SELECT COUNT(*) FROM projects"))
        result["project_count"] = count_result.scalar_one()
    except Exception:
        result["connected"] = False

    return result


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session."""
    async with session_factory() as session:
        yield session
