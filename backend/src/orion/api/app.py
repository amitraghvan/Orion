"""FastAPI application factory for ORION BAS AI Copilot."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orion.api.middleware import CorrelationIdMiddleware, SecurityHeadersMiddleware
from orion.api.routers import (
    auth_router,
    camera_router,
    experiments_router,
    health_router,
    metadata_router,
    telemetry_ws_router,
)
from orion.api.routers.telemetry_ws import manager as ws_manager
from orion.core.config import OrionSettings, get_settings
from orion.core.exceptions import OrionBaseException
from orion.core.in_memory_event_bus import InMemoryEventBus
from orion.core.logger import configure_logging, get_logger
from orion.db.persistence_subscriber import EventPersistenceSubscriber
from orion.db.session import init_db, reset_db_engine
from orion.di.container import (
    get_coordinator,
    set_coordinator_instance,
    set_event_bus_instance,
    set_persistence_subscriber_instance,
    set_protocol_service_instance,
)
from orion.events.schemas import (
    ActivityRecognized,
    AlertRaised,
    BaseEvent,
    ExperimentUpdated,
    HealthChanged,
    NextStepRecommended,
    ObservationCaptured,
    ProtocolDeviationDetected,
    ProtocolStateChanged,
    RecordingStarted,
    RecordingStopped,
    StepTransitioned,
)
from orion.protocol.service import ProtocolService
from orion_ai.activity.configs import ActivityConfig
from orion_ai.activity.runtime import TemporalHARRuntime
from orion_ai.detection.yolo_detector import YOLOEdgeDetector
from orion_ai.pose.yolo_pose import YOLOPoseEstimator
from orion_ai.runtime.coordinator import PerceptionPipelineCoordinator
from orion_ai.tracking.byte_tracker import ByteTracker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager handling application startup and shutdown."""
    settings: OrionSettings = getattr(app.state, "settings", None) or get_settings()

    # Configure structured logging
    configure_logging(
        log_level=settings.logging.level,
        log_format=settings.logging.format,
        log_file=settings.logging.file_path,
        rotation_bytes=settings.logging.rotation_bytes,
        backup_count=settings.logging.backup_count,
    )

    logger = get_logger("orion.lifecycle")
    logger.info(
        "Station Copilot initializing",
        station_id=settings.station_id,
        env=settings.env,
        version=settings.version,
    )

    # Initialize in-memory event bus
    event_bus = InMemoryEventBus()
    set_event_bus_instance(event_bus)

    # Initialize database engine and session factory bound to current settings
    engine, session_factory = init_db(settings)

    # Initialize and start persistence subscriber
    persistence_subscriber = EventPersistenceSubscriber(session_factory)
    await persistence_subscriber.start()
    set_persistence_subscriber_instance(persistence_subscriber)

    # Database schema check / auto-creation
    auto_create = (
        settings.db.auto_create_tables
        if settings.db.auto_create_tables is not None
        else settings.env in ("development", "testing")
    )
    if auto_create:
        logger.info("Auto-creating database tables (dev/test mode)")
        async with engine.begin() as conn:
            import orion.db.models  # noqa: F401
            from orion.db.base import Base

            await conn.run_sync(Base.metadata.create_all)
    else:
        logger.info("Validating provisioned database schema (production mode)")
        from sqlalchemy import inspect
        from sqlalchemy.engine import Connection

        def _check_tables(sync_conn: Connection) -> None:
            inspector = inspect(sync_conn)
            existing_tables = set(inspector.get_table_names())
            required_tables = {"events", "protocol_decisions", "runs", "experiments"}
            missing = required_tables - existing_tables
            if missing:
                raise RuntimeError(
                    f"Database schema incomplete or unprovisioned. Missing tables: {sorted(missing)}. "
                    "Run 'alembic upgrade head' before starting the application in production."
                )

        async with engine.begin() as conn:
            await conn.run_sync(_check_tables)

    # Formally decoupled event taxonomy:
    # High-frequency transient telemetry (FrameCaptured, DetectionCompleted, PoseCompleted)
    # is streamed over WebSockets and NOT written to SQLite.
    # Only durable domain events and state mutations are persisted to SQLite.
    durable_events: list[type[BaseEvent]] = [
        AlertRaised,
        HealthChanged,
        ExperimentUpdated,
        ActivityRecognized,
        RecordingStarted,
        RecordingStopped,
        ProtocolStateChanged,
        StepTransitioned,
        ProtocolDeviationDetected,
        NextStepRecommended,
    ]
    for event_cls in durable_events:
        event_bus.subscribe(event_cls, persistence_subscriber.on_event)

    # Initialize ProtocolService
    protocol_service = ProtocolService(
        event_bus=event_bus,
        persistence_subscriber=persistence_subscriber,
    )
    canonical_path = Path("configs/protocols/bas_crystal_growth_v1.yaml")
    if not canonical_path.is_file():
        canonical_path = Path("configs/protocols/bas_e01_a.yaml")
    if canonical_path.is_file():
        try:
            protocol_service.load_protocol_file(canonical_path)
            logger.info(
                "Loaded canonical experiment protocol into ProtocolService",
                protocol=str(canonical_path),
            )
        except Exception as exc:
            logger.warning("Failed to auto-load canonical protocol", error=str(exc))
    set_protocol_service_instance(protocol_service)

    # Register WebSocket broadcast forwarder
    async def _ws_event_forwarder(event: BaseEvent) -> None:
        if isinstance(event, ObservationCaptured):
            await ws_manager.broadcast_observation(event.observation)
            return
        if event.event_type in ("FrameCaptured", "DetectionCompleted", "PoseCompleted"):
            return
        from orion.db.persistence_subscriber import _sanitize_for_json

        try:
            raw_event = event.model_dump()
        except Exception:
            raw_event = event.__dict__

        payload = _sanitize_for_json(raw_event)
        payload["type"] = event.event_type
        payload["station_id"] = event.station_id
        payload["timestamp_utc"] = event.timestamp.isoformat()
        await ws_manager.broadcast_json(payload)

    event_bus.subscribe(BaseEvent, _ws_event_forwarder)

    # Initialize Perception Pipeline Coordinator if not pre-injected
    coordinator: PerceptionPipelineCoordinator | None = None
    try:
        coordinator = get_coordinator()
    except Exception:
        coordinator = None

    if coordinator is None:
        from orion_ai.camera.camera_manager import authoritative_camera_manager

        cam_source: str | int = settings.camera.source
        if str(cam_source).isdigit():
            cam_source = int(cam_source)

        authoritative_camera_manager.configure(
            source=cam_source,
            width=settings.camera.width,
            height=settings.camera.height,
            fps=settings.camera.fps,
            loop=True,
        )
        camera = authoritative_camera_manager

        accelerator = settings.hardware.accelerator
        if accelerator == "cpu" and settings.env != "testing":
            import torch

            if torch.backends.mps.is_available():
                accelerator = "mps"
                logger.info("Auto-detected Apple Silicon GPU: using MPS acceleration profile")

        detector = YOLOEdgeDetector(
            confidence_threshold=0.45,
            device=accelerator,
        )
        det_weights = Path("models/weights/yolo11n.pt")
        if det_weights.exists():
            try:
                await detector.load(str(det_weights))
            except Exception as exc:
                logger.warning("Failed to load detector weights", error=str(exc))

        pose_estimator = YOLOPoseEstimator(
            confidence_threshold=0.25,
            device=accelerator,
        )
        pose_weights = Path("models/weights/yolo11n-pose.pt")
        if pose_weights.exists():
            try:
                await pose_estimator.load(str(pose_weights))
            except Exception as exc:
                logger.warning("Failed to load pose estimator weights", error=str(exc))

        tracker = ByteTracker(high_score_thresh=0.4, match_thresh=0.3)

        har_runtime: TemporalHARRuntime | None = None
        bas_weights = Path("models/bas_experiment/best.pt")
        default_weights = Path("models/weights/stgcn_har_v1.pt")
        har_weights = bas_weights if bas_weights.exists() else default_weights
        model_id = "BAS-HAR-v1.0" if bas_weights.exists() else "stgcn_har_v1"
        if har_weights.exists():
            try:
                har_config = ActivityConfig(
                    model_id=model_id,
                    window_size_frames=32,
                    stride_frames=8,
                    confidence_threshold=0.3,
                )
                har_runtime = TemporalHARRuntime(
                    config=har_config,
                    model_path=str(har_weights),
                    device=accelerator,
                    station_id=settings.station_id,
                )
                logger.info(
                    "Loaded HAR model weights from %s (model_id: %s)", har_weights, model_id
                )
            except Exception as exc:
                logger.warning("Failed to initialize HAR runtime", error=str(exc))

        coordinator = PerceptionPipelineCoordinator(
            camera=camera,
            detector=detector,
            pose_estimator=pose_estimator,
            tracker=tracker,
            event_bus=event_bus,
            station_id=settings.station_id,
            har_runtime=har_runtime,
        )
        set_coordinator_instance(coordinator)

    coordinator_started = False
    try:
        await coordinator.start()
        coordinator_started = True
        logger.info("Perception pipeline coordinator started successfully")
    except Exception as exc:
        logger.error("Failed to start perception pipeline coordinator", error=str(exc))

    yield

    if coordinator_started and coordinator is not None:
        await coordinator.stop()
    set_coordinator_instance(None)
    set_persistence_subscriber_instance(None)
    await persistence_subscriber.stop()
    await engine.dispose()
    reset_db_engine()
    await event_bus.shutdown()
    logger.info("Station Copilot shutting down safely", station_id=settings.station_id)


def create_app(settings: OrionSettings | None = None) -> FastAPI:
    """FastAPI application factory."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="ORION BAS AI Copilot",
        description=(
            "Offline AI Human Activity Recognition System for Bharatiya Antariksh Station. "
            "Phase 0: Scientific Production Foundation."
        ),
        version=settings.version,
        docs_url="/docs" if settings.env != "production" else None,
        redoc_url="/redoc" if settings.env != "production" else None,
        openapi_url="/openapi.json" if settings.env != "production" else None,
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Middleware registration (innermost to outermost execution order)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global domain exception handler
    @app.exception_handler(OrionBaseException)
    async def orion_exception_handler(request: Request, exc: OrionBaseException) -> JSONResponse:
        logger = get_logger("orion.exception")
        logger.error(
            "Domain exception intercepted",
            exception=exc.__class__.__name__,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=exc.to_dict(),
        )

    # Metrics endpoints
    @app.get("/api/v1/metrics", tags=["Observability"], summary="Prometheus Metrics")
    @app.get("/metrics", tags=["Observability"], summary="Prometheus Metrics Scrape Endpoint")
    async def prometheus_metrics() -> Response:
        """Prometheus metrics scrape endpoint."""
        from orion.core.metrics import get_latest_metrics

        return Response(
            content=get_latest_metrics(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    # Router registration
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(camera_router, prefix="/api/v1")
    app.include_router(metadata_router, prefix="/api/v1")
    app.include_router(experiments_router, prefix="/api/v1")
    app.include_router(telemetry_ws_router)

    return app
