"""Health check endpoints for orchestrators and ground monitoring."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from orion.core.config import OrionSettings
from orion.di.container import get_settings

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """System health status response."""

    status: str = Field(default="NOMINAL", description="Overall system health status")
    station_id: str
    environment: str
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    response_model=HealthResponse,
    summary="Liveness Probe",
)
async def liveness_probe(settings: OrionSettings = Depends(get_settings)) -> HealthResponse:
    """Basic process liveness verification."""
    return HealthResponse(
        status="NOMINAL",
        station_id=settings.station_id,
        environment=settings.env,
        version=settings.version,
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    response_model=HealthResponse,
    summary="Readiness Probe",
)
async def readiness_probe(settings: OrionSettings = Depends(get_settings)) -> HealthResponse:
    """Subsystem readiness verification for flight operations."""
    return HealthResponse(
        status="NOMINAL",
        station_id=settings.station_id,
        environment=settings.env,
        version=settings.version,
    )
