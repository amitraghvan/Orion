import os
from collections.abc import AsyncGenerator

os.environ["ORION_ENV"] = "testing"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import orion.db.models
from orion.api.app import create_app
from orion.core.auth import create_access_token
from orion.core.config import ApiSettings, OrionSettings
from orion.db.base import Base


@pytest.fixture(scope="session")
def test_settings() -> OrionSettings:
    """Fixture providing isolated test settings."""
    from orion.core.config import CameraSettings

    return OrionSettings(
        ORION_ENV="testing",
        ORION_STATION_ID="BAS-TEST-BENCH",
        api=ApiSettings(secret_key="test-insecure-secret-key-32-characters-minimum"),
        camera=CameraSettings(source="assets/sample_replay.mp4", width=640, height=480, fps=30),
    )


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite async engine for isolated test execution."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    """HTTPX AsyncClient bound to the FastAPI application with operator credentials."""
    app = create_app(settings=test_settings)
    operator_token = create_access_token(
        subject="test-operator",
        role="operator",
        secret_key=test_settings.api.secret_key,
    )
    headers = {"Authorization": f"Bearer {operator_token}"}
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", headers=headers
        ) as client:
            yield client
