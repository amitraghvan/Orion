"""System metadata and station telemetry router."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from orion.core.auth import require_viewer
from orion.core.config import OrionSettings
from orion.di.container import get_settings

router = APIRouter(prefix="/metadata", tags=["Metadata"])


class SystemMetadataResponse(BaseModel):
    """System identification and flight certification metadata."""

    project: str = Field(default="orion-bas-ai")
    codename: str = Field(default="ORION")
    version: str
    station_id: str
    environment: str
    offline_first: bool = True
    phase: str = Field(default="Phase 0: Scientific Production Foundation")
    hardware_accelerator: str


@router.get(
    "/info",
    status_code=status.HTTP_200_OK,
    response_model=SystemMetadataResponse,
    summary="System Information",
)
async def get_system_info(
    settings: OrionSettings = Depends(get_settings),
    _user: object = Depends(require_viewer),
) -> SystemMetadataResponse:
    """Return runtime metadata and hardware acceleration profile."""
    return SystemMetadataResponse(
        version=settings.version,
        station_id=settings.station_id,
        environment=settings.env,
        hardware_accelerator=settings.hardware.accelerator,
    )
