"""Async database engine and session management for SQLAlchemy 2.0."""

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from orion.core.config import OrionSettings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: OrionSettings) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Explicitly initialize or reconfigure the database engine and session factory with settings."""
    global _engine, _session_factory
    connect_args = {}
    if "sqlite" in settings.db.url:
        connect_args["check_same_thread"] = False
        db_file_str = settings.db.url.split(":///")[-1]
        if db_file_str and db_file_str != ":memory:" and not db_file_str.startswith("?"):
            Path(db_file_str).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(
        settings.db.url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return _engine, _session_factory


def reset_db_engine() -> None:
    """Reset singleton engine and session factory (used for testing and lifecycle shutdown)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    """Return or initialize the singleton AsyncEngine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if "sqlite" in settings.db.url:
            connect_args["check_same_thread"] = False
            db_file_str = settings.db.url.split(":///")[-1]
            if db_file_str and db_file_str != ":memory:" and not db_file_str.startswith("?"):
                Path(db_file_str).parent.mkdir(parents=True, exist_ok=True)

        _engine = create_async_engine(
            settings.db.url,
            echo=False,
            future=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return or initialize the async sessionmaker factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async dependency generator yielding an isolated database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
