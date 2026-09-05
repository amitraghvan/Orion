"""Routers package for ORION BAS AI Copilot."""

from orion.api.routers.health import router as health_router
from orion.api.routers.metadata import router as metadata_router
from orion.api.routers.telemetry_ws import router as telemetry_ws_router

__all__ = [
    "health_router",
    "metadata_router",
    "telemetry_ws_router",
]
