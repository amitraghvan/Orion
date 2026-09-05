"""Contract tests validating Pydantic event schemas."""

from uuid import UUID

import pytest

from orion.events import (
    AlertRaised,
    FrameCaptured,
)


@pytest.mark.contract
def test_frame_captured_schema() -> None:
    event = FrameCaptured(
        camera_id="CAM-01",
        frame_index=1,
        width=1920,
        height=1080,
        pixel_format="RGB8",
        timestamp_sensor_ns=1700000000000,
        latency_ms=12.5,
    )
    assert event.event_type == "FrameCaptured"
    assert isinstance(event.event_id, UUID)
    assert event.width == 1920


@pytest.mark.contract
def test_alert_raised_schema() -> None:
    event = AlertRaised(
        subsystem="camera",
        severity="WARNING",
        code="FRAME_DROP",
        message="Camera dropped 5 consecutive frames",
    )
    assert event.event_type == "AlertRaised"
    assert event.severity == "WARNING"
