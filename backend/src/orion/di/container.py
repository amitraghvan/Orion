"""FastAPI Dependency Injection providers for ORION BAS AI Copilot.

Provides clean inversion of control for Settings, DB Session, Logger, and EventBus.
"""

from collections.abc import AsyncGenerator

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orion.core.config import OrionSettings
from orion.core.config import get_settings as core_get_settings
from orion.core.event_bus import EventBusInterface
from orion.core.logger import get_logger as core_get_logger
from orion.db.session import get_db_session as db_get_session

# Concrete or mock event bus reference placeholder
_event_bus_instance: EventBusInterface | None = None


def set_event_bus_instance(bus: EventBusInterface) -> None:
    """Register global event bus provider."""
    global _event_bus_instance
    _event_bus_instance = bus


def get_settings() -> OrionSettings:
    """DI provider for cached application settings."""
    return core_get_settings()


async def get_db(
    session: AsyncSession = Depends(db_get_session),
) -> AsyncGenerator[AsyncSession, None]:
    """DI provider for scoped async database sessions."""
    yield session


def get_logger(
    settings: OrionSettings = Depends(get_settings),
) -> structlog.stdlib.BoundLogger:
    """DI provider for bound structured telemetry logger."""
    return core_get_logger(f"orion.{settings.station_id}")


def get_event_bus() -> EventBusInterface:
    """DI provider for internal event bus. Raises NotImplementedError if not configured."""
    if _event_bus_instance is None:
        raise NotImplementedError("NOT IMPLEMENTED: Event bus runtime provider not registered")
    return _event_bus_instance
