"""Hand perception interface for ORION BAS AI Copilot."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from orion_ai.hand.schemas import HandObservation
from orion_ai.pose.schemas import HumanPose
from orion_ai.tracking.schemas import TrackedObject


class HandPerceptionInterface(ABC):
    """Abstract interface for hand extraction and state perception."""

    @abstractmethod
    def extract_hands(
        self,
        frame_buffer: Any,
        poses: list[HumanPose],
        tracks: list[TrackedObject],
        frame_index: int,
        timestamp: datetime,
        source_id: str,
    ) -> list[HandObservation]:
        """Extract hand spatial regions and states from poses and tracking."""
        raise NotImplementedError("NOT IMPLEMENTED: HandPerceptionInterface.extract_hands")
