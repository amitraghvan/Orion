"""Global pytest fixtures and test configuration for ORION BAS AI Copilot."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from orion.api.app import create_app
from orion.core.config import ApiSettings, OrionSettings
from orion.db.base import Base


@pytest.fixture(scope="session")
def test_settings() -> OrionSettings:
    """Fixture providing isolated test settings."""
    return OrionSettings(
        ORION_ENV="testing",
        ORION_STATION_ID="BAS-TEST-BENCH",
        api=ApiSettings(secret_key="test-insecure-secret-key-32-characters-minimum"),
    )


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite async engine for isolated test execution."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Scoped async database session."""
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def async_client(test_settings: OrionSettings) -> AsyncGenerator[AsyncClient, None]:
    """HTTPX AsyncClient bound to the FastAPI application."""
    app = create_app(settings=test_settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
