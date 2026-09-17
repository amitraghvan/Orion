"""Structured multi-sink logging system with file rotation and console output."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import Any

from app.core.paths import paths

# Standard logging formats
FILE_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] [%(threadName)s] %(message)s"
CONSOLE_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


LOGRECORD_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
    "extra",
}


class OrionLoggerAdapter(logging.LoggerAdapter):
    """Adapter to inject experiment_id, camera_id, and model_id into log records."""

    STANDARD_KWARGS = {"exc_info", "stack_info", "stacklevel", "extra"}

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        extra = kwargs.setdefault("extra", {})
        if self.extra:
            for k, v in self.extra.items():
                if k not in LOGRECORD_RESERVED:
                    extra.setdefault(k, v)
                else:
                    extra.setdefault(f"meta_{k}", v)

        # Absorb any arbitrary kwargs not accepted by standard logging.Logger
        custom_kwargs = {}
        keys_to_remove = [k for k in list(kwargs.keys()) if k not in self.STANDARD_KWARGS]
        for k in keys_to_remove:
            custom_kwargs[k] = kwargs.pop(k)

        for k, v in custom_kwargs.items():
            safe_k = k if k not in LOGRECORD_RESERVED else f"meta_{k}"
            extra[safe_k] = v

        context_parts = []
        for k, v in custom_kwargs.items():
            context_parts.append(f"{k}={v}")
        if "experiment_id" in extra and "experiment_id" not in custom_kwargs:
            context_parts.append(f"exp={extra['experiment_id']}")
        if "camera_id" in extra and "camera_id" not in custom_kwargs:
            context_parts.append(f"cam={extra['camera_id']}")
        if "model_id" in extra and "model_id" not in custom_kwargs:
            context_parts.append(f"model={extra['model_id']}")

        if context_parts:
            msg = f"{msg} | {' '.join(context_parts)}"
        return msg, kwargs


def configure_logging(
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """Initialize root logging and configure rotating file handlers for all submodules."""
    global _configured
    if _configured:
        return

    log_dir = paths.logs_dir
    log_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # 1. Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT, datefmt="%H:%M:%S"))
    root_logger.addHandler(console_handler)

    # Helper to add rotating file handler
    def _add_file_sink(filename: str, sink_level: int = log_level) -> RotatingFileHandler:
        filepath = log_dir / filename
        h = RotatingFileHandler(
            filepath, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        h.setLevel(sink_level)
        h.setFormatter(logging.Formatter(FILE_LOG_FORMAT, datefmt=DATE_FORMAT))
        return h

    # 2. Main application log
    app_handler = _add_file_sink("application.log")
    root_logger.addHandler(app_handler)

    # 3. Error only log
    error_handler = _add_file_sink("error.log", sink_level=logging.ERROR)
    root_logger.addHandler(error_handler)

    # 4. Domain-specific loggers
    def _attach_domain_logger(name: str, filename: str) -> None:
        logger = logging.getLogger(name)
        h = _add_file_sink(filename)
        logger.addHandler(h)

    _attach_domain_logger("app.camera", "camera.log")
    _attach_domain_logger("app.intelligence", "ai.log")
    _attach_domain_logger("app.models", "ai.log")
    _attach_domain_logger("app.experiments", "experiment.log")

    # Mute noisy third party loggers
    for noisy in ["urllib3", "PIL", "matplotlib", "asyncio"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
    logging.getLogger("app.core.logging").info("ORION structured logging subsystem initialized.")


def get_logger(name: str, **context: Any) -> OrionLoggerAdapter:
    """Obtain a contextual logger adapter with custom metadata bindings."""
    if not _configured:
        configure_logging()
    base_logger = logging.getLogger(name)
    return OrionLoggerAdapter(base_logger, extra=context)
