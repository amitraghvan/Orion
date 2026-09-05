"""Audio System Architecture for ORION BAS AI Copilot.

Offline-first architecture: defines priority queuing, cooldown enforcement, and
speech provider interfaces for astronaut acoustic advisory annunciations.
Zero TTS implementation.
"""

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field


class AudioPriority(IntEnum):
    """Audio alert priority levels. Lower integer means higher priority."""

    EMERGENCY = 0
    CRITICAL = 1
    WARNING = 2
    ADVISORY = 3
    INFO = 4


class AudioAlertMessage(BaseModel):
    """Payload contract for audio alert dispatch."""

    alert_id: str
    priority: AudioPriority
    chime_name: str | None = None
    spoken_text: str | None = None
    interrupt: bool = False
    cooldown_seconds: float = 10.0
    payload: dict[str, Any] = Field(default_factory=dict)


class AudioQueueInterface(ABC):
    """Interface for managing the sequence of pending audio annunciation items."""

    @abstractmethod
    async def enqueue(self, message: AudioAlertMessage) -> bool:
        """Add audio message to pending queue."""
        raise NotImplementedError("NOT IMPLEMENTED: AudioQueueInterface.enqueue")

    @abstractmethod
    async def dequeue(self) -> AudioAlertMessage | None:
        """Fetch next ready audio message."""
        raise NotImplementedError("NOT IMPLEMENTED: AudioQueueInterface.dequeue")

    @abstractmethod
    def clear(self) -> None:
        """Purge pending queue."""
        raise NotImplementedError("NOT IMPLEMENTED: AudioQueueInterface.clear")


class PriorityQueueInterface(ABC):
    """Interface for sorting and preempting audio items based on severity."""

    @abstractmethod
    def push_priority(self, message: AudioAlertMessage) -> None:
        """Insert message sorted by strict priority hierarchy."""
        raise NotImplementedError("NOT IMPLEMENTED: PriorityQueueInterface.push_priority")

    @abstractmethod
    def peek_highest(self) -> AudioAlertMessage | None:
        """Inspect highest priority item without removing it."""
        raise NotImplementedError("NOT IMPLEMENTED: PriorityQueueInterface.peek_highest")


class CooldownManagerInterface(ABC):
    """Interface for preventing repetitive audio chimes from flooding the cockpit."""

    @abstractmethod
    def is_in_cooldown(self, alert_code: str) -> bool:
        """Return True if identical alert was enunciated within cooldown window."""
        raise NotImplementedError("NOT IMPLEMENTED: CooldownManagerInterface.is_in_cooldown")

    @abstractmethod
    def record_emission(self, alert_code: str, duration_seconds: float) -> None:
        """Mark alert code as active with timestamp."""
        raise NotImplementedError("NOT IMPLEMENTED: CooldownManagerInterface.record_emission")


class SpeechProviderInterface(ABC):
    """Interface for offline text-to-speech synthesis (e.g. espeak-ng or offline Piper)."""

    @abstractmethod
    async def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesize offline audio file from text string."""
        raise NotImplementedError("NOT IMPLEMENTED: SpeechProviderInterface.synthesize")

    @abstractmethod
    async def cancel(self) -> None:
        """Abort active speech synthesis."""
        raise NotImplementedError("NOT IMPLEMENTED: SpeechProviderInterface.cancel")
