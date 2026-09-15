import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from orion.core.config import get_settings
from orion.db.base import Base
# Import all models to register with Base.metadata
from orion.db.models import *  # noqa: F403

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    settings = get_settings()
    url = config.get_main_option("sqlalchemy.url") or settings.db.url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    settings = get_settings()
    configuration = config.get_section(config.config_ini_section, {})
    url = config.get_main_option("sqlalchemy.url") or settings.db.url
    if url.startswith("sqlite:") and not url.startswith("sqlite+aiosqlite:"):
        url = url.replace("sqlite:", "sqlite+aiosqlite:", 1)
    elif url.startswith("postgresql:") and not url.startswith("postgresql+asyncpg:"):
        url = url.replace("postgresql:", "postgresql+asyncpg:", 1)
    configuration["sqlalchemy.url"] = url
    if "sqlite" in url:
        from pathlib import Path

        db_file_str = url.split(":///")[-1]
        if db_file_str and db_file_str != ":memory:" and not db_file_str.startswith("?"):
            Path(db_file_str).parent.mkdir(parents=True, exist_ok=True)

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()



def run_migrations_online() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, run_async_migrations()).result()
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
