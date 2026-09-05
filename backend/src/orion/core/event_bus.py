"""Internal typed event bus architecture for ORION BAS AI Copilot.

Architecture only: defines publish/subscribe protocols and typed dispatch interfaces.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

from orion.events.schemas import BaseEvent

E = TypeVar("E", bound=BaseEvent)
EventHandler = Callable[[E], Awaitable[None]]


class EventBusInterface(ABC):
    """Abstract interface for high-performance internal typed event communication."""

    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Publish a typed event to all subscribed listeners."""
        raise NotImplementedError("NOT IMPLEMENTED: Event bus runtime publish")

    @abstractmethod
    def subscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Register an async handler for a specific event type."""
        raise NotImplementedError("NOT IMPLEMENTED: Event bus runtime subscribe")

    @abstractmethod
    def unsubscribe(self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Deregister an async handler."""
        raise NotImplementedError("NOT IMPLEMENTED: Event bus runtime unsubscribe")
