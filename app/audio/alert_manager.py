"""Central Alert Manager coordinating acoustic annunciations and visual operator alarms."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from app.audio.tts_engine import tts_engine
from app.core.event_bus import event_bus
from app.core.logging import get_logger
from pydantic import BaseModel, Field

logger = get_logger("app.audio.alerts")


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertItem(BaseModel):
    """Structured operational alarm record."""

    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).strftime("%H:%M:%S"))
    severity: AlertSeverity = AlertSeverity.INFO
    message: str
    source: str = "ORION_COPILOT"
    acknowledged: bool = False


class AlertManager:
    """Stores active alerts and dispatches corresponding audio annunciations."""

    def __init__(self) -> None:
        self._alerts: list[AlertItem] = []
        self._lock = threading.RLock()
        self._setup_event_subscriptions()

    def _setup_event_subscriptions(self) -> None:
        event_bus.subscribe(dict, self._handle_bus_event)

    def _handle_bus_event(self, event: dict[str, Any]) -> None:
        etype = event.get("type")
        if etype == "VOICE_ALERT":
            text = event.get("text", "")
            prio = event.get("priority", 3)
            tts_engine.speak(text, priority=prio)
        elif etype == "ALERT":
            msg = event.get("message", "")
            sev = event.get("severity", "INFO")
            self.raise_alert(msg, severity=AlertSeverity(sev))

    def raise_alert(
        self, message: str, severity: AlertSeverity = AlertSeverity.INFO, source: str = "COPILOT"
    ) -> AlertItem:
        """Create and register an alert item."""
        with self._lock:
            alert = AlertItem(
                severity=severity,
                message=message,
                source=source,
            )
            self._alerts.insert(0, alert)
            # Keep maximum 100 historical alerts
            if len(self._alerts) > 100:
                self._alerts.pop()

            logger.info("Raised alarm", severity=severity.value, message=message)
            return alert

    def get_active_alerts(self) -> list[AlertItem]:
        with self._lock:
            return list(self._alerts)

    def acknowledge_all(self) -> None:
        with self._lock:
            for a in self._alerts:
                a.acknowledged = True

    def clear(self) -> None:
        with self._lock:
            self._alerts.clear()


# Global alert manager singleton
alert_manager = AlertManager()
