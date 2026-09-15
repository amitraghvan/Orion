"""Health check endpoints for orchestrators, ground monitoring, and HUD telemetry."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from orion.api.routers.telemetry_ws import manager as ws_manager
from orion.core.config import OrionSettings
from orion.di.container import (
    get_coordinator,
    get_db,
    get_event_bus,
    get_persistence_subscriber,
    get_protocol_service,
    get_settings,
)
from orion.health.interfaces import SubsystemReport, SubsystemStatus

router = APIRouter(prefix="/health", tags=["Health"])


class SubsystemHealthDetail(BaseModel):
    """Component-specific diagnostic status across all 10 core subsystems."""

    application: str = "HEALTHY"
    database: str = "UNKNOWN"
    event_bus: str = "UNKNOWN"
    models: str = "UNKNOWN"
    detector: str = "UNKNOWN"
    pose: str = "UNKNOWN"
    har_model: str = "UNKNOWN"
    camera: str = "UNKNOWN"
    pipeline: str = "UNKNOWN"
    tracker: str = "UNKNOWN"
    persistence: str = "UNKNOWN"
    protocol: str = "UNKNOWN"
    websocket: str = "UNKNOWN"
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """System health status response."""

    status: str = Field(default="NOMINAL", description="Overall system health status")
    station_id: str
    environment: str
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trust_score: float = 100.0
    warehouse_connected: bool = True
    details: SubsystemHealthDetail = Field(default_factory=SubsystemHealthDetail)
    subsystems: dict[str, SubsystemReport] = Field(default_factory=dict)


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    response_model=HealthResponse,
    summary="Liveness Probe",
)
async def liveness_probe(settings: OrionSettings = Depends(get_settings)) -> HealthResponse:
    """Basic process liveness verification.

    Verifies ONLY that the FastAPI process and async event loop are alive.
    Never fails due to camera disconnect, model latency, or database degradation.
    """
    details = SubsystemHealthDetail(application="HEALTHY")
    return HealthResponse(
        status="NOMINAL",
        station_id=settings.station_id,
        environment=settings.env,
        version=settings.version,
        trust_score=100.0,
        warehouse_connected=True,
        details=details,
    )


async def _evaluate_system_health(
    settings: OrionSettings,
    db: AsyncSession | None,
) -> tuple[str, SubsystemHealthDetail, dict[str, SubsystemReport], float]:
    """Interrogate all runtime subsystems and collect health reports."""
    details = SubsystemHealthDetail()
    subsystem_reports: dict[str, SubsystemReport] = {}
    now = datetime.now(UTC)

    # 1. Application Process Health
    details.application = "HEALTHY"
    subsystem_reports["application"] = SubsystemReport(
        subsystem_id="application",
        status=SubsystemStatus.HEALTHY,
        timestamp=now,
        metrics={"uptime_nominal": True},
        details={"version": settings.version, "env": settings.env},
    )

    # 2. Database Connectivity
    if db is not None:
        try:
            await db.execute(text("SELECT 1"))
            details.database = "HEALTHY"
            subsystem_reports["database"] = SubsystemReport(
                subsystem_id="database",
                status=SubsystemStatus.HEALTHY,
                timestamp=now,
                metrics={"connected": 1.0},
            )
        except Exception as exc:
            details.database = "DEGRADED"
            subsystem_reports["database"] = SubsystemReport(
                subsystem_id="database",
                status=SubsystemStatus.DEGRADED,
                timestamp=now,
                metrics={"connected": 0.0},
                error_message=str(exc),
            )
    else:
        details.database = "OFFLINE"
        subsystem_reports["database"] = SubsystemReport(
            subsystem_id="database",
            status=SubsystemStatus.OFFLINE,
            timestamp=now,
            metrics={"connected": 0.0},
            error_message="Database session provider returned None",
        )

    # 3. Event Bus
    try:
        bus = get_event_bus()
        if hasattr(bus, "get_health_report"):
            bus_rep = bus.get_health_report()
            details.event_bus = bus_rep.status.value
            subsystem_reports["event_bus"] = bus_rep
        else:
            is_active = getattr(bus, "is_active", True)
            details.event_bus = "HEALTHY" if is_active else "OFFLINE"
            subsystem_reports["event_bus"] = SubsystemReport(
                subsystem_id="event_bus",
                status=SubsystemStatus.HEALTHY if is_active else SubsystemStatus.OFFLINE,
                timestamp=now,
            )
    except Exception as exc:
        details.event_bus = "OFFLINE"
        subsystem_reports["event_bus"] = SubsystemReport(
            subsystem_id="event_bus",
            status=SubsystemStatus.OFFLINE,
            timestamp=now,
            error_message=str(exc),
        )

    # 4. Perception Pipeline & Camera & Models
    coordinator = None
    try:
        coordinator = get_coordinator()
    except Exception:
        coordinator = None

    if coordinator is not None:
        # Pipeline
        if hasattr(coordinator, "get_health_report"):
            pipe_rep = coordinator.get_health_report()
            details.pipeline = pipe_rep.status.value
            subsystem_reports["pipeline"] = pipe_rep
        else:
            is_run = getattr(coordinator, "is_running", False)
            details.pipeline = "HEALTHY" if is_run else "OFFLINE"
            subsystem_reports["pipeline"] = SubsystemReport(
                subsystem_id="pipeline",
                status=SubsystemStatus.HEALTHY if is_run else SubsystemStatus.OFFLINE,
                timestamp=now,
            )

        # Camera
        cam = getattr(coordinator, "camera", None)
        if cam and hasattr(cam, "get_health_report"):
            cam_rep = cam.get_health_report()
            details.camera = cam_rep.status.value
            subsystem_reports["camera"] = cam_rep
        elif cam:
            details.camera = "HEALTHY" if getattr(cam, "is_active", False) else "OFFLINE"
            subsystem_reports["camera"] = SubsystemReport(
                subsystem_id="camera",
                status=SubsystemStatus.HEALTHY if getattr(cam, "is_active", False) else SubsystemStatus.OFFLINE,
                timestamp=now,
            )
        else:
            details.camera = "OFFLINE"

        # Detector
        detector = getattr(coordinator, "detector", None)
        if detector and hasattr(detector, "get_health_report"):
            det_rep = detector.get_health_report()
            details.detector = det_rep.status.value
            subsystem_reports["detector"] = det_rep
        else:
            details.detector = "UNKNOWN"

        # Pose Estimator
        pose = getattr(coordinator, "pose_estimator", None)
        if pose and hasattr(pose, "get_health_report"):
            pose_rep = pose.get_health_report()
            details.pose = pose_rep.status.value
            subsystem_reports["pose"] = pose_rep
        else:
            details.pose = "UNKNOWN"

        # Tracker
        tracker = getattr(coordinator, "tracker", None)
        details.tracker = "HEALTHY" if tracker is not None else "OFFLINE"
        subsystem_reports["tracker"] = SubsystemReport(
            subsystem_id="tracker",
            status=SubsystemStatus.HEALTHY if tracker is not None else SubsystemStatus.OFFLINE,
            timestamp=now,
        )

        # HAR Runtime (Optional)
        har = getattr(coordinator, "har_runtime", None)
        if har and hasattr(har, "get_health_report"):
            har_rep = har.get_health_report()
            details.har_model = har_rep.status.value
            subsystem_reports["har_model"] = har_rep
        else:
            details.har_model = "OFFLINE"
            subsystem_reports["har_model"] = SubsystemReport(
                subsystem_id="har_model",
                status=SubsystemStatus.OFFLINE,
                timestamp=now,
                details={"optional": True},
                error_message="HAR runtime not configured or inactive",
            )
    else:
        details.pipeline = "OFFLINE"
        details.camera = "OFFLINE"
        details.detector = "OFFLINE"
        details.pose = "OFFLINE"
        details.tracker = "OFFLINE"
        details.har_model = "OFFLINE"

    # Backwards compatibility for 'models'
    det_model_path = Path("models/weights/yolo11n.pt")
    pose_model_path = Path("models/weights/yolo11n-pose.pt")
    if (
        details.detector in ("HEALTHY", "DEGRADED")
        and details.pose in ("HEALTHY", "DEGRADED")
    ) or (det_model_path.exists() and pose_model_path.exists()):
        details.models = "HEALTHY"
    else:
        details.models = "MISSING"

    # 5. Persistence Worker
    try:
        persistence = get_persistence_subscriber()
        if hasattr(persistence, "get_health_report"):
            pers_rep = persistence.get_health_report()
            details.persistence = pers_rep.status.value
            subsystem_reports["persistence"] = pers_rep
        else:
            is_pers_run = getattr(persistence, "is_running", False)
            details.persistence = "HEALTHY" if is_pers_run else "OFFLINE"
            subsystem_reports["persistence"] = SubsystemReport(
                subsystem_id="persistence",
                status=SubsystemStatus.HEALTHY if is_pers_run else SubsystemStatus.OFFLINE,
                timestamp=now,
            )
    except Exception as exc:
        details.persistence = "OFFLINE"
        subsystem_reports["persistence"] = SubsystemReport(
            subsystem_id="persistence",
            status=SubsystemStatus.OFFLINE,
            timestamp=now,
            error_message=str(exc),
        )

    # 6. Protocol Service
    try:
        protocol_svc = get_protocol_service()
        if hasattr(protocol_svc, "get_health_report"):
            proto_rep = protocol_svc.get_health_report()
            details.protocol = proto_rep.status.value
            subsystem_reports["protocol"] = proto_rep
        else:
            details.protocol = "HEALTHY"
            subsystem_reports["protocol"] = SubsystemReport(
                subsystem_id="protocol",
                status=SubsystemStatus.HEALTHY,
                timestamp=now,
            )
    except Exception as exc:
        details.protocol = "OFFLINE"
        subsystem_reports["protocol"] = SubsystemReport(
            subsystem_id="protocol",
            status=SubsystemStatus.OFFLINE,
            timestamp=now,
            error_message=str(exc),
        )

    # 7. WebSocket Telemetry Feeder
    if hasattr(ws_manager, "get_health_report"):
        ws_rep = ws_manager.get_health_report()
        details.websocket = ws_rep.status.value
        subsystem_reports["websocket"] = ws_rep
    else:
        details.websocket = "HEALTHY"
        subsystem_reports["websocket"] = SubsystemReport(
            subsystem_id="websocket",
            status=SubsystemStatus.HEALTHY,
            timestamp=now,
        )

    # Calculate overall status and trust score
    required_statuses = [
        details.database,
        details.event_bus,
        details.pipeline,
        details.camera,
        details.detector,
        details.pose,
        details.persistence,
    ]

    has_error_or_offline = any(st in ("OFFLINE", "ERROR", "UNHEALTHY", "MISSING") for st in required_statuses)
    has_degraded = any(st == "DEGRADED" for st in required_statuses) or details.har_model == "DEGRADED"

    if has_error_or_offline:
        overall_status = "DEGRADED" if details.pipeline in ("HEALTHY", "DEGRADED") else "UNHEALTHY"
    elif has_degraded:
        overall_status = "DEGRADED"
    else:
        overall_status = "NOMINAL"

    # Compute trust score (percentage of nominal core subsystems)
    healthy_count = sum(1 for st in required_statuses if st == "HEALTHY")
    degraded_count = sum(1 for st in required_statuses if st == "DEGRADED")
    trust_score = round(
        ((healthy_count * 1.0 + degraded_count * 0.5) / max(len(required_statuses), 1)) * 100.0,
        1,
    )

    return overall_status, details, subsystem_reports, trust_score


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness Probe",
)
async def readiness_probe(
    response: Response,
    settings: OrionSettings = Depends(get_settings),
    db: AsyncSession | None = Depends(get_db),
) -> HealthResponse:
    """Subsystem readiness verification for flight operations.

    Returns HTTP 200 when ready (or nominal/degraded operational mode),
    and HTTP 503 if required dependencies are unready or offline.
    """
    overall_status, details, subsystem_reports, trust_score = await _evaluate_system_health(
        settings, db
    )

    # Critical failure that prevents any processing
    if overall_status == "UNHEALTHY":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        station_id=settings.station_id,
        environment=settings.env,
        version=settings.version,
        trust_score=trust_score,
        warehouse_connected=(details.database == "HEALTHY"),
        details=details,
        subsystems=subsystem_reports,
    )


@router.get(
    "",
    response_model=HealthResponse,
    summary="System Health Overview",
)
async def system_health_overview(
    settings: OrionSettings = Depends(get_settings),
    db: AsyncSession | None = Depends(get_db),
) -> HealthResponse:
    """Complete diagnostic system health report for ground station HUD polling."""
    overall_status, details, subsystem_reports, trust_score = await _evaluate_system_health(
        settings, db
    )
    return HealthResponse(
        status=overall_status,
        station_id=settings.station_id,
        environment=settings.env,
        version=settings.version,
        trust_score=trust_score,
        warehouse_connected=(details.database == "HEALTHY"),
        details=details,
        subsystems=subsystem_reports,
    )
