"""Unit tests for InMemoryEventBus async dispatch and failure containment."""

import pytest

from orion.core.in_memory_event_bus import InMemoryEventBus
from orion.events.schemas import BaseEvent, DetectionCompleted, PoseCompleted


@pytest.mark.asyncio
@pytest.mark.unit
async def test_event_bus_publish_subscribe() -> None:
    """Verify typed events are dispatched to subscribed handlers."""
    bus = InMemoryEventBus()
    received_detections: list[DetectionCompleted] = []

    async def detection_handler(evt: DetectionCompleted) -> None:
        received_detections.append(evt)

    bus.subscribe(DetectionCompleted, detection_handler)

    evt1 = DetectionCompleted(
        frame_index=1,
        detection_count=2,
        classes_detected=["person", "bottle"],
        inference_time_ms=12.5,
    )
    await bus.publish(evt1)

    assert len(received_detections) == 1
    assert received_detections[0].frame_index == 1
    assert received_detections[0].detection_count == 2
    assert bus.published_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_event_bus_global_handler() -> None:
    """Verify BaseEvent handlers receive all event types."""
    bus = InMemoryEventBus()
    received_all: list[BaseEvent] = []

    async def global_handler(evt: BaseEvent) -> None:
        received_all.append(evt)

    bus.subscribe(BaseEvent, global_handler)

    await bus.publish(
        DetectionCompleted(
            frame_index=1,
            detection_count=1,
            classes_detected=["person"],
            inference_time_ms=8.0,
        )
    )
    await bus.publish(
        PoseCompleted(
            frame_index=1,
            person_count=1,
            topology="coco_17",
            inference_time_ms=15.0,
        )
    )

    assert len(received_all) == 2
    assert bus.published_count == 2


@pytest.mark.asyncio
@pytest.mark.unit
async def test_event_bus_error_isolation() -> None:
    """Verify that a failing handler does not abort other subscribers."""
    bus = InMemoryEventBus()
    successful_calls: list[int] = []

    async def faulty_handler(evt: DetectionCompleted) -> None:
        raise RuntimeError("Simulated crash in subscriber")

    async def healthy_handler(evt: DetectionCompleted) -> None:
        successful_calls.append(evt.frame_index)

    bus.subscribe(DetectionCompleted, faulty_handler)
    bus.subscribe(DetectionCompleted, healthy_handler)

    evt = DetectionCompleted(
        frame_index=99,
        detection_count=0,
        classes_detected=[],
        inference_time_ms=5.0,
    )
    # Must not raise RuntimeError
    await bus.publish(evt)

    assert len(successful_calls) == 1
    assert successful_calls[0] == 99
    assert bus.published_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_event_bus_unsubscribe_and_shutdown() -> None:
    """Verify unsubscribing and shutting down cleanly stops event dispatch."""
    bus = InMemoryEventBus()
    calls: list[int] = []

    async def handler(evt: DetectionCompleted) -> None:
        calls.append(evt.frame_index)

    bus.subscribe(DetectionCompleted, handler)
    bus.unsubscribe(DetectionCompleted, handler)

    await bus.publish(
        DetectionCompleted(
            frame_index=1,
            detection_count=0,
            classes_detected=[],
            inference_time_ms=1.0,
        )
    )
    assert len(calls) == 0

    await bus.shutdown()
    assert not bus.is_active
