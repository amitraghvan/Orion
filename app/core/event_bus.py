"""Thread-safe event bus with pub/sub architecture and optional Qt signal bridge."""

from __future__ import annotations

import inspect
import queue
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar

from app.core.logging import get_logger

logger = get_logger("app.core.event_bus")

T = TypeVar("T")


class EventBus:
    """Thread-safe synchronous and asynchronous event dispatching hub."""

    def __init__(self) -> None:
        self._subscribers: dict[type[Any], list[Callable[[Any], Any]]] = defaultdict(list)
        self._lock = threading.RLock()
        self._event_queue: queue.Queue[Any] = queue.Queue(maxsize=1000)
        self._qt_bridges: list[Any] = []

    def register_qt_bridge(self, bridge: Any) -> None:
        """Attach a Qt QObject signal bridge for thread-safe main thread dispatch."""
        with self._lock:
            if bridge not in self._qt_bridges:
                self._qt_bridges.append(bridge)

    def subscribe(self, event_type: type[T], handler: Callable[[T], Any]) -> Callable[[], None]:
        """Subscribe a handler callback to an event type. Returns an unsubscribe function."""
        with self._lock:
            self._subscribers[event_type].append(handler)

        def _unsubscribe() -> None:
            with self._lock:
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)

        return _unsubscribe

    def publish(self, event: Any) -> None:
        """Publish an event immediately to all registered subscribers."""
        event_cls = type(event)
        handlers_to_call: list[Callable[[Any], Any]] = []

        with self._lock:
            # Direct subscribers
            handlers_to_call.extend(self._subscribers.get(event_cls, []))
            # Base class subscribers
            for registered_type, handlers in self._subscribers.items():
                if registered_type is not event_cls and isinstance(event, registered_type):
                    handlers_to_call.extend(handlers)

            # Qt signal bridge notification
            for bridge in self._qt_bridges:
                try:
                    if hasattr(bridge, "emit_event"):
                        bridge.emit_event(event)
                except Exception as exc:
                    logger.error("Qt signal bridge delivery error", error=str(exc))

        for handler in handlers_to_call:
            try:
                res = handler(event)
                if inspect.iscoroutine(res):
                    # If an async coroutine is returned in a sync context, log warning
                    pass
            except Exception as exc:
                logger.error(
                    "Event handler error",
                    handler=handler.__name__,
                    event=event_cls.__name__,
                    error=str(exc),
                )


# Global event bus singleton
event_bus = EventBus()
