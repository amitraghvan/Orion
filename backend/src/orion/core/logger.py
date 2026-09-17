"""Aerospace-grade production logging system for ORION BAS AI Copilot.

Combines Structlog structured context with Loguru rotating sinks.
Supports JSON logging for telemetry ingestion and human-readable console logging.
Thread-safe, async-safe correlation ID and mission context binding.
"""

import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any, cast

import structlog
from loguru import logger as loguru_logger

# Contextual variables for telemetry correlation
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
run_id_ctx: ContextVar[str | None] = ContextVar("run_id", default=None)
experiment_id_ctx: ContextVar[str | None] = ContextVar("experiment_id", default=None)
model_version_ctx: ContextVar[str | None] = ContextVar("model_version", default=None)
dataset_version_ctx: ContextVar[str | None] = ContextVar("dataset_version", default=None)


def set_correlation_id(correlation_id: str | None) -> None:
    """Bind a request or frame correlation ID to the current async context."""
    correlation_id_ctx.set(correlation_id)


def set_mission_context(
    run_id: str | None = None,
    experiment_id: str | None = None,
    model_version: str | None = None,
    dataset_version: str | None = None,
) -> None:
    """Bind flight mission context variables to current async context."""
    if run_id is not None:
        run_id_ctx.set(run_id)
    if experiment_id is not None:
        experiment_id_ctx.set(experiment_id)
    if model_version is not None:
        model_version_ctx.set(model_version)
    if dataset_version is not None:
        dataset_version_ctx.set(dataset_version)


def _add_telemetry_context(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that injects ambient correlation and mission context."""
    corr_id = correlation_id_ctx.get()
    if corr_id:
        event_dict["correlation_id"] = corr_id

    run_id = run_id_ctx.get()
    if run_id:
        event_dict["run_id"] = run_id

    exp_id = experiment_id_ctx.get()
    if exp_id:
        event_dict["experiment_id"] = exp_id

    mod_ver = model_version_ctx.get()
    if mod_ver:
        event_dict["model_version"] = mod_ver

    data_ver = dataset_version_ctx.get()
    if data_ver:
        event_dict["dataset_version"] = data_ver

    return event_dict


def _add_logger_name(logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    if hasattr(logger, "name"):
        event_dict["logger"] = logger.name
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "console",
    log_file: str | None = None,
    rotation_bytes: int = 52428800,
    backup_count: int = 10,
) -> None:
    """Configure Structlog and Loguru sinks according to system profile."""
    # Reset existing Loguru handlers
    loguru_logger.remove()

    # Formatter selection
    if log_format == "json":
        loguru_logger.add(
            sys.stdout,
            level=log_level,
            serialize=True,
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )
    else:
        loguru_logger.add(
            sys.stdout,
            level=log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=(log_format == "pretty"),
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

    # Optional file rotation sink
    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        loguru_logger.add(
            str(file_path),
            level=log_level,
            rotation=rotation_bytes,
            retention=backup_count,
            compression="tar.gz",
            serialize=(log_format == "json"),
            enqueue=True,
            backtrace=True,
        )

    # Configure Structlog processors
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_telemetry_context,
        structlog.stdlib.add_log_level,
        _add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    elif log_format == "pretty":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog bound logger with module identity."""
    return cast("structlog.stdlib.BoundLogger", structlog.get_logger(name or "orion"))
