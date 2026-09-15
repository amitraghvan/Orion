"""FastAPI Dependency Injection providers for ORION BAS AI Copilot.

Provides clean inversion of control for Settings, DB Session, Logger, and EventBus.
"""

from collections.abc import AsyncGenerator
from typing import Any

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
_protocol_service_instance: Any = None
_coordinator_instance: Any = None
_persistence_subscriber_instance: Any = None


def set_event_bus_instance(bus: EventBusInterface) -> None:
    """Register global event bus provider."""
    global _event_bus_instance
    _event_bus_instance = bus


def set_protocol_service_instance(service: Any) -> None:
    """Register global protocol service provider."""
    global _protocol_service_instance
    _protocol_service_instance = service


def set_coordinator_instance(coordinator: Any) -> None:
    """Register global perception pipeline coordinator provider."""
    global _coordinator_instance
    _coordinator_instance = coordinator


def set_persistence_subscriber_instance(subscriber: Any) -> None:
    """Register global event persistence subscriber provider."""
    global _persistence_subscriber_instance
    _persistence_subscriber_instance = subscriber


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


def get_protocol_service() -> Any:
    """DI provider for ProtocolService."""
    if _protocol_service_instance is None:
        raise RuntimeError("ProtocolService not initialized in application lifespan")
    return _protocol_service_instance


def get_coordinator() -> Any:
    """DI provider for PerceptionPipelineCoordinator."""
    if _coordinator_instance is None:
        raise RuntimeError("PerceptionPipelineCoordinator not initialized in application lifespan")
    return _coordinator_instance


def get_persistence_subscriber() -> Any:
    """DI provider for EventPersistenceSubscriber."""
    if _persistence_subscriber_instance is None:
        raise RuntimeError("EventPersistenceSubscriber not initialized in application lifespan")
    return _persistence_subscriber_instance


