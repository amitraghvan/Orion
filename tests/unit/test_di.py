"""Unit tests for Dependency Injection providers."""

import pytest

from orion.di.container import get_event_bus, get_logger, get_settings


@pytest.mark.unit
def test_get_settings_di() -> None:
    """Verify get_settings provider returns valid OrionSettings."""
    settings = get_settings()
    assert settings is not None
    assert hasattr(settings, "station_id")


@pytest.mark.unit
def test_get_logger_di() -> None:
    """Verify get_logger provider returns bound logger."""
    settings = get_settings()
    logger = get_logger(settings)
    assert logger is not None


@pytest.mark.unit
def test_get_event_bus_not_implemented() -> None:
    """Verify get_event_bus raises NotImplementedError when no bus is registered."""
    import orion.di.container as di_container

    saved_bus = di_container._event_bus_instance
    try:
        di_container._event_bus_instance = None
        with pytest.raises(NotImplementedError, match="NOT IMPLEMENTED"):
            get_event_bus()
    finally:
        di_container._event_bus_instance = saved_bus

