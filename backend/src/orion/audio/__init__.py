"""Audio subsystem package for ORION BAS AI Copilot."""

from orion.audio.interfaces import (
    AudioAlertMessage,
    AudioPriority,
    AudioQueueInterface,
    CooldownManagerInterface,
    PriorityQueueInterface,
    SpeechProviderInterface,
)

__all__ = [
    "AudioAlertMessage",
    "AudioPriority",
    "AudioQueueInterface",
    "CooldownManagerInterface",
    "PriorityQueueInterface",
    "SpeechProviderInterface",
]
