"""FastAPI application factory for ORION BAS AI Copilot."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orion.api.middleware import CorrelationIdMiddleware
from orion.api.routers import health_router, metadata_router, telemetry_ws_router
from orion.core.config import OrionSettings, get_settings
from orion.core.exceptions import OrionBaseException
from orion.core.logger import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager handling application startup and shutdown."""
    settings = get_settings()

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

    yield

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

    # Middleware registration
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

    # Router registration
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(metadata_router, prefix="/api/v1")
    app.include_router(telemetry_ws_router)

    return app
