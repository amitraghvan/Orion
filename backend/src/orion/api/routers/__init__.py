"""Routers package for ORION BAS AI Copilot."""

from orion.api.routers.auth import router as auth_router
from orion.api.routers.camera import router as camera_router
from orion.api.routers.experiments import router as experiments_router
from orion.api.routers.health import router as health_router
from orion.api.routers.metadata import router as metadata_router
from orion.api.routers.telemetry_ws import router as telemetry_ws_router

__all__ = [
    "auth_router",
    "camera_router",
    "experiments_router",
    "health_router",
    "metadata_router",
    "telemetry_ws_router",
]
