"""Unit tests for layered configuration loading and priorities."""

import pytest

from orion.core.config import get_settings


@pytest.mark.unit
def test_default_settings_loading() -> None:
    """Verify default settings instantiation."""
    settings = get_settings()
    assert settings.station_id is not None
    assert settings.api.port == 8000
    assert settings.seed == 42
    assert settings.logging.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@pytest.mark.unit
def test_env_override_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that environment variables take priority over default values."""
    monkeypatch.setenv("ORION_STATION_ID", "BAS-OVERRIDE-NODE")
    monkeypatch.setenv("ORION_ENV", "testing")

    # Clear LRU cache to reload
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.station_id == "BAS-OVERRIDE-NODE"
    assert settings.env == "testing"

    # Reset cache
    get_settings.cache_clear()
