"""Air-gap enforcement ensuring complete isolation from external cloud and network services."""

from __future__ import annotations

import os

from app.core.logging import get_logger

logger = get_logger("app.core.airgap")


def enforce_airgap() -> None:
    """Configure runtime flags and libraries to prevent any outbound internet communication."""
    # 1. Ultralytics offline enforcement
    os.environ["ULTRALYTICS_OFFLINE"] = "1"
    os.environ["YOLO_OFFLINE"] = "1"
    os.environ["YOLO_VERBOSE"] = "False"
    os.environ["NO_COLOR"] = "1"

    # 2. PyTorch / HuggingFace / HF Hub offline flags
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TORCH_HUB_OFFLINE"] = "1"

    try:
        from ultralytics import settings

        settings.update({"sync": False, "checks": False})
        logger.debug("Ultralytics telemetry and update checks disabled")
    except Exception:
        pass

    logger.info("Air-gap isolation flags actively enforced")
