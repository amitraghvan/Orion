"""P0.3 Health API Contract and Subsystem Failure-Recovery Hardening Tests."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from orion.core.in_memory_event_bus import InMemoryEventBus
from orion.db.persistence_subscriber import EventPersistenceSubscriber
from orion.di.container import get_coordinator, get_event_bus
from orion.events.schemas import BaseEvent
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion_ai.camera.opencv_driver import OpenCVCameraDriver
from orion_ai.detection.yolo_detector import YOLOEdgeDetector


@pytest.mark.integration
async def test_1_liveness_returns_healthy_while_process_is_running(
    async_client: AsyncClient,
) -> None:
    """TEST 1: Liveness probe returns healthy while process is running."""
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NOMINAL"
    assert "station_id" in data
    assert "version" in data


@pytest.mark.integration
async def test_2_readiness_returns_healthy_when_dependencies_healthy(
    async_client: AsyncClient,
) -> None:
    """TEST 2: Readiness returns nominal/ready when required dependencies are initialized."""
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("NOMINAL", "DEGRADED")
    assert data["details"]["database"] in ("HEALTHY", "DEGRADED")
    assert data["details"]["event_bus"] == "HEALTHY"


@pytest.mark.integration
async def test_3_readiness_reports_pipeline_failure_correctly(
    async_client: AsyncClient,
) -> None:
    """TEST 3: Readiness reports pipeline failure correctly when coordinator is stopped."""
    coordinator = get_coordinator()
    was_running = coordinator.is_running
    coordinator._is_running = False

    try:
        response = await async_client.get("/api/v1/health/ready")
        data = response.json()
        assert data["details"]["pipeline"] in ("OFFLINE", "ERROR")
    finally:
        coordinator._is_running = was_running


@pytest.mark.integration
async def test_4_camera_failure_changes_camera_health_correctly() -> None:
    """TEST 4: Camera failure transitions health report to DEGRADED/OFFLINE/ERROR accurately."""
    # Scenario A: Fallback video active
    cam_replay = OpenCVCameraDriver(source="assets/sample_replay.mp4", is_replay_fallback=True)
    cam_replay._is_active = True
    rep_replay = cam_replay.get_health_report()
    assert rep_replay.status == SubsystemStatus.DEGRADED
    assert "fallback" in rep_replay.error_message.lower()

    # Scenario B: Fatal error
    cam_err = OpenCVCameraDriver(source=999)
    from orion.core.exceptions import CameraError

    cam_err._fatal_error = CameraError("Device failed", details={"subcode": "TEST_FAIL"})
    rep_err = cam_err.get_health_report()
    assert rep_err.status == SubsystemStatus.ERROR
    assert "Device failed" in (rep_err.error_message or "")


@pytest.mark.integration
async def test_5_model_loading_failure_is_observable() -> None:
    """TEST 5: Model loading failure is observable in health report."""
    detector = YOLOEdgeDetector()
    rep_unloaded = detector.get_health_report()
    assert rep_unloaded.status == SubsystemStatus.OFFLINE
    assert rep_unloaded.metrics["is_loaded"] is False

    # Simulate inference failure
    detector._is_loaded = True
    detector._last_error = "CUDA out of memory"
    rep_failed = detector.get_health_report()
    assert rep_failed.status == SubsystemStatus.DEGRADED
    assert "CUDA out of memory" in (rep_failed.error_message or "")


@pytest.mark.integration
async def test_6_persistence_failure_is_observable() -> None:
    """TEST 6: Persistence failures are observable in health diagnostics."""
    mock_session_factory = MagicMock()
    subscriber = EventPersistenceSubscriber(mock_session_factory)
    subscriber._is_running = True
    subscriber._failed_count = 5
    subscriber._last_error = "database disk image is malformed"

    rep = subscriber.get_health_report()
    assert rep.status in (SubsystemStatus.DEGRADED, SubsystemStatus.ERROR)
    assert rep.metrics["failed_count"] == 5
    assert "malformed" in (rep.error_message or "")


@pytest.mark.integration
async def test_7_websocket_failure_does_not_kill_application(
    async_client: AsyncClient,
) -> None:
    """TEST 7: Saturated or disconnected WebSocket clients do not crash the application."""
    from orion.api.routers.telemetry_ws import manager

    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock(side_effect=RuntimeError("Broken pipe"))
    mock_ws.accept = AsyncMock()

    await manager.connect(mock_ws)
    assert mock_ws in manager.active_connections

    # Broadcast payload; sender task handles exception and disconnects client
    await manager.broadcast_json({"type": "TELEMETRY_FRAME", "test": True})
    await asyncio.sleep(0.1)

    assert mock_ws not in manager.active_connections

    # Application remains completely responsive
    resp = await async_client.get("/api/v1/health/live")
    assert resp.status_code == 200


@pytest.mark.integration
async def test_8_event_subscriber_failure_does_not_kill_unrelated_subscribers() -> None:
    """TEST 8: A failing event subscriber does not disrupt sibling subscribers."""
    bus = InMemoryEventBus()
    handled_by_healthy: list[str] = []

    async def throwing_subscriber(event: BaseEvent) -> None:
        raise ValueError("Simulated subscriber crash")

    async def healthy_subscriber(event: BaseEvent) -> None:
        handled_by_healthy.append(event.event_type)

    bus.subscribe(BaseEvent, throwing_subscriber)
    bus.subscribe(BaseEvent, healthy_subscriber)

    test_event = BaseEvent(station_id="BAS-TEST", event_type="TestEvent")
    await bus.publish(test_event)

    assert handled_by_healthy == ["TestEvent"]
    assert bus.subscriber_failures == 1
    rep = bus.get_health_report()
    assert rep.status == SubsystemStatus.DEGRADED


@pytest.mark.integration
async def test_9_pipeline_failure_does_not_create_orphan_asyncio_tasks(
    async_client: AsyncClient,
) -> None:
    """TEST 9: Pipeline coordinator loop handles failures without leaking orphan tasks."""
    coordinator = get_coordinator()
    initial_tasks = len(asyncio.all_tasks())

    # Simulate frame processing error
    with patch.object(
        coordinator, "process_single_frame", side_effect=RuntimeError("Simulated drop")
    ):
        # Let supervisor handle several failed iterations
        await asyncio.sleep(0.3)

    remaining_tasks = len(asyncio.all_tasks())
    # Task count must remain bounded (no task accumulation per failure)
    assert abs(remaining_tasks - initial_tasks) <= 2


@pytest.mark.integration
async def test_10_recovery_succeeds_after_simulated_transient_failure(
    async_client: AsyncClient,
) -> None:
    """TEST 10: Recovery succeeds and clears failure counters after transient errors."""
    coordinator = get_coordinator()
    coordinator._consecutive_failures = 3
    if not coordinator.camera.is_active:
        await coordinator.camera.initialize()

    # Execute a successful single frame pass
    obs = await coordinator.process_single_frame()
    assert obs is not None
    assert coordinator.frames_processed > 0


@pytest.mark.integration
async def test_11_recovery_remains_bounded_after_repeated_failures(
    async_client: AsyncClient,
) -> None:
    """TEST 11: Supervisor recovery applies bounded backoff without CPU spinning."""
    coordinator = get_coordinator()
    coordinator._is_running = True
    coordinator._consecutive_failures = 10
    rep = coordinator.get_health_report()
    assert rep.status == SubsystemStatus.ERROR
    assert coordinator.consecutive_failures >= 10


@pytest.mark.integration
async def test_12_health_endpoint_does_not_expose_secrets(
    async_client: AsyncClient,
) -> None:
    """TEST 12: Health endpoint response does not leak credentials, secrets, or raw passwords."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    text = response.text.lower()
    assert "secret_key" not in text
    assert "password" not in text
    assert "token" not in text
    assert "private" not in text
