"""In-Memory Typed Asynchronous Event Bus for ORION BAS AI Copilot.

Provides zero-broker, air-gapped, sub-millisecond event dispatch across
in-process subscribers (persistence workers, telemetry WebSocket feeds, and audio annunciator).
"""

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, TypeVar, cast

from orion.core.event_bus import EventBusInterface
from orion.core.logger import get_logger
from orion.core.metrics import EVENT_BUS_EVENTS_TOTAL, EVENT_BUS_FAILURES_TOTAL
from orion.events.schemas import BaseEvent
from orion.health.interfaces import SubsystemReport, SubsystemStatus

E = TypeVar("E", bound=BaseEvent)
EventHandler = Callable[[E], Awaitable[None]]

logger = get_logger("orion.core.event_bus")


class InMemoryEventBus(EventBusInterface):
    """High-throughput in-memory asynchronous publish/subscribe event bus."""

    def __init__(self) -> None:
        self._handlers: dict[type[BaseEvent], list[EventHandler[Any]]] = defaultdict(list)
        self._global_handlers: list[EventHandler[BaseEvent]] = []
        self._is_active: bool = True
        self._published_count: int = 0
        self._processed_count: int = 0
        self._failure_count: int = 0
        self._last_published_utc: datetime | None = None
        self._last_processed_utc: datetime | None = None

    @property
    def is_active(self) -> bool:
        """Return bus operational status."""
        return self._is_active

    @property
    def published_count(self) -> int:
        """Return total number of successfully dispatched events."""
        return self._published_count

    @property
    def processed_count(self) -> int:
        """Return total handler invocations."""
        return self._processed_count

    @property
    def subscriber_failures(self) -> int:
        """Return total isolated handler failures."""
        return self._failure_count

    @property
    def subscriber_count(self) -> int:
        """Return total active subscribers across all registered events."""
        count = len(self._global_handlers)
        for handlers in self._handlers.values():
            count += len(handlers)
        return count

    @property
    def last_published_timestamp(self) -> datetime | None:
        """Return timestamp of the most recent event published."""
        return self._last_published_utc

    @property
    def last_processing_timestamp(self) -> datetime | None:
        """Return timestamp of the most recent handler completion."""
        return self._last_processed_utc

    def subscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Register an asynchronous subscriber for a specific event schema."""
        if event_type is BaseEvent:
            cast_handler = cast("EventHandler[BaseEvent]", handler)
            if cast_handler not in self._global_handlers:
                self._global_handlers.append(cast_handler)
        elif handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
        logger.debug("Subscriber registered", event_type=event_type.__name__)

    def unsubscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Deregister an asynchronous subscriber."""
        if event_type is BaseEvent:
            cast_handler = cast("EventHandler[BaseEvent]", handler)
            if cast_handler in self._global_handlers:
                self._global_handlers.remove(cast_handler)
        elif handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
        logger.debug("Subscriber deregistered", event_type=event_type.__name__)

    async def publish(self, event: BaseEvent) -> None:
        """Publish a typed event to all subscribed listeners with error containment."""
        if not self._is_active:
            logger.warning("Event dropped: bus is inactive", event_id=str(event.event_id))
            return

        event_cls = type(event)
        self._last_published_utc = datetime.now(UTC)
        EVENT_BUS_EVENTS_TOTAL.labels(event_type=event_cls.__name__).inc()

        target_handlers: list[EventHandler[Any]] = list(self._global_handlers)

        # Collect exact and polymorphic handlers
        for registered_type, handlers in self._handlers.items():
            if issubclass(event_cls, registered_type):
                target_handlers.extend(handlers)

        if not target_handlers:
            self._published_count += 1
            return

        # Execute all handlers concurrently with error isolation
        tasks = [self._safe_execute(handler, event) for handler in target_handlers]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._published_count += 1

    async def _safe_execute(self, handler: EventHandler[Any], event: BaseEvent) -> None:
        """Invoke a single handler protecting against unhandled exceptions."""
        try:
            await handler(event)
            self._processed_count += 1
            self._last_processed_utc = datetime.now(UTC)
        except Exception as exc:
            self._failure_count += 1
            EVENT_BUS_FAILURES_TOTAL.labels(event_type=type(event).__name__).inc()
            logger.error(
                "Event handler failed",
                handler=getattr(handler, "__name__", str(handler)),
                event_type=type(event).__name__,
                event_id=str(event.event_id),
                error=str(exc),
            )

    async def shutdown(self) -> None:
        """Drain active tasks and halt event dispatch."""
        self._is_active = False
        logger.info("Event bus shutdown completed", total_dispatched=self._published_count)

    def get_health_report(self) -> SubsystemReport:
        """Produce structured subsystem health diagnostic report."""
        now = datetime.now(UTC)
        if not self._is_active:
            status = SubsystemStatus.OFFLINE
            err = "Event bus is inactive or shut down"
        elif self._failure_count > 0:
            status = SubsystemStatus.DEGRADED
            err = f"Subscriber handler exceptions encountered ({self._failure_count})"
        else:
            status = SubsystemStatus.HEALTHY
            err = None

        return SubsystemReport(
            subsystem_id="event_bus",
            status=status,
            timestamp=now,
            last_success=self._last_processed_utc,
            latency_ms=0.0,
            metrics={
                "events_published": self._published_count,
                "events_processed": self._processed_count,
                "subscriber_failures": self._failure_count,
                "subscriber_count": self.subscriber_count,
            },
            details={
                "is_active": self._is_active,
                "registered_types": len(self._handlers),
            },
            error_message=err,
        )
