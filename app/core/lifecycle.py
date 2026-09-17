"""Application lifecycle management: deterministic startup and graceful shutdown."""

from __future__ import annotations

import atexit
import threading
from collections.abc import Callable
from typing import Any

from app.core.config import get_config
from app.core.logging import get_logger
from app.core.paths import paths
from app.core.state_manager import ApplicationState, state_manager

logger = get_logger("app.core.lifecycle")


class LifecycleManager:
    """Coordinates component startup, hardware detection, and graceful resource release."""

    def __init__(self) -> None:
        self._startup_hooks: list[Callable[[], Any]] = []
        self._shutdown_hooks: list[Callable[[], Any]] = []
        self._is_started = False
        self._is_shutting_down = False
        self._lock = threading.Lock()

        # Register exit handler
        atexit.register(self.shutdown)

    def register_startup_hook(self, hook: Callable[[], Any]) -> None:
        """Register a callback to run during startup."""
        self._startup_hooks.append(hook)

    def register_shutdown_hook(self, hook: Callable[[], Any]) -> None:
        """Register a callback to run during shutdown (executed in LIFO order)."""
        self._shutdown_hooks.append(hook)

    def startup(self) -> None:
        """Execute deterministic startup sequence."""
        with self._lock:
            if self._is_started:
                return
            state_manager.set_app_state(ApplicationState.INITIALIZING)
            logger.info(" Commencing ORION startup sequence...")

            # Enforce air-gap isolation
            from app.core.airgap import enforce_airgap

            enforce_airgap()

            # 1. Ensure required directories
            paths.recordings_dir
            paths.logs_dir
            paths.reports_dir
            paths.resources_dir

            # 2. Validate configuration
            cfg = get_config()
            logger.info(
                " Configuration validated", station_id=cfg.system.station_id, mode=cfg.system.mode
            )

            # 3. Detect hardware
            self._detect_hardware()

            # 4. Run registered subsystem startup hooks
            for hook in self._startup_hooks:
                try:
                    hook()
                except Exception as exc:
                    logger.error("Startup hook failed", hook=hook.__name__, error=str(exc))

            self._is_started = True
            state_manager.set_app_state(ApplicationState.READY)
            logger.info(" ORION Startup complete. Status: READY.")

    def shutdown(self) -> None:
        """Execute graceful shutdown sequence in reverse order."""
        with self._lock:
            if self._is_shutting_down or not self._is_started:
                return
            self._is_shutting_down = True
            try:
                logger.info(" Commencing ORION graceful shutdown sequence...")
                state_manager.set_app_state(ApplicationState.SHUTDOWN)
            except Exception:
                pass

            # Execute shutdown hooks in LIFO (reverse) order
            for hook in reversed(self._shutdown_hooks):
                try:
                    logger.debug(
                        "Executing shutdown hook", hook=getattr(hook, "__name__", str(hook))
                    )
                    hook()
                except Exception as exc:
                    try:
                        logger.error("Shutdown hook failed", hook=str(hook), error=str(exc))
                    except Exception:
                        pass

            self._is_started = False
            try:
                logger.info(" ORION Shutdown complete. All resources cleanly released.")
            except Exception:
                pass

    def _detect_hardware(self) -> None:
        """Inspect system compute capabilities (CPU, Apple Silicon MPS, NVIDIA CUDA, TensorRT)."""
        cuda_avail = False
        tensorrt_avail = False
        active_device = "CPU"

        try:
            import torch

            if torch.cuda.is_available():
                cuda_avail = True
                active_device = f"CUDA ({torch.cuda.get_device_name(0)})"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                active_device = "Apple Silicon (MPS)"
            else:
                active_device = "CPU (Accelerated)"
        except ImportError:
            pass

        try:
            import tensorrt  # noqa: F401

            tensorrt_avail = True
        except (ImportError, Exception):
            pass

        logger.info(
            "Hardware capabilities detected",
            device=active_device,
            cuda=cuda_avail,
            tensorrt=tensorrt_avail,
        )
        state_manager.update_telemetry(
            cuda_available=cuda_avail,
            tensorrt_available=tensorrt_avail,
            active_device=active_device,
        )


# Global lifecycle manager singleton
lifecycle = LifecycleManager()
