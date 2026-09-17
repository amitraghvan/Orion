"""Asynchronous persistence subscriber storing telemetry and perception events into the database."""

import asyncio
import contextlib
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orion.core.logger import get_logger
from orion.core.metrics import OBSERVATIONS_PERSISTED_TOTAL
from orion.db.models.alert import Alert
from orion.db.models.decision import ProtocolDecisionModel
from orion.db.models.event import Event
from orion.db.models.system_health import SystemHealth
from orion.events.schemas import (
    AlertRaised,
    BaseEvent,
    HealthChanged,
)
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion.protocol.decision_engine import ProtocolDecision

logger = get_logger("orion.db.subscriber")


def _sanitize_for_json(val: Any) -> Any:
    """Recursively convert numpy types, models, UUIDs, datetimes, and nested structures to standard JSON primitives."""
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {str(k): _sanitize_for_json(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [_sanitize_for_json(item) for item in val]
    if hasattr(val, "item") and callable(val.item):
        return val.item()
    if hasattr(val, "tolist") and callable(val.tolist):
        return [_sanitize_for_json(item) for item in val.tolist()]
    if hasattr(val, "model_dump") and callable(val.model_dump):
        return _sanitize_for_json(val.model_dump(mode="json"))
    if hasattr(val, "to_dict") and callable(val.to_dict):
        return _sanitize_for_json(val.to_dict())
    return val


class EventPersistenceSubscriber:
    """Asynchronous subscriber writing typed telemetry events to SQLAlchemy storage."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self._queue: asyncio.Queue[BaseEvent] = asyncio.Queue(maxsize=1000)
        self._worker_task: asyncio.Task[None] | None = None
        self._is_running: bool = False
        self._persisted_count: int = 0
        self._failed_count: int = 0
        self._last_success_utc: datetime | None = None
        self._last_error: str | None = None

    @property
    def is_running(self) -> bool:
        """Return worker active state."""
        return self._is_running

    @property
    def pending_events(self) -> int:
        """Return count of unpersisted events in queue."""
        return self._queue.qsize()

    @property
    def persisted_count(self) -> int:
        """Return total successfully persisted events."""
        return self._persisted_count

    @property
    def failed_count(self) -> int:
        """Return total failed persistence operations."""
        return self._failed_count

    @property
    def last_success_timestamp(self) -> datetime | None:
        """Return timestamp of the most recent successful persist."""
        return self._last_success_utc

    @property
    def last_error(self) -> str | None:
        """Return the most recent persistence error message."""
        return self._last_error

    async def start(self) -> None:
        """Start the background persistence queue consumer."""
        if self._is_running:
            return
        self._is_running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("Database persistence subscriber active")

    async def stop(self) -> None:
        """Drain queue and shut down persistence worker."""
        self._is_running = False
        if self._worker_task:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=5.0)
            except TimeoutError:
                logger.warning("Persistence subscriber queue drain timed out")
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None
        logger.info("Database persistence subscriber stopped")

    async def on_event(self, event: BaseEvent) -> None:
        """Enqueue event for background database persistence without blocking inference."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                "Persistence queue full, dropping audit event", event_type=event.event_type
            )

    async def _process_queue(self) -> None:
        """Background worker consuming events and persisting them in batches."""
        while self._is_running or not self._queue.empty():
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            except TimeoutError:
                if not self._is_running and self._queue.empty():
                    break
                continue
            except asyncio.CancelledError:
                break

            persisted = False
            for retry_idx in range(3):
                try:
                    await self._persist_event(event)
                    self._persisted_count += 1
                    self._last_success_utc = datetime.now(UTC)
                    self._last_error = None
                    OBSERVATIONS_PERSISTED_TOTAL.labels(station_id=event.station_id).inc()
                    persisted = True
                    break
                except Exception as exc:
                    self._last_error = str(exc)
                    if retry_idx < 2:
                        logger.warning(
                            "Transient database write error; retrying",
                            attempt=retry_idx + 1,
                            event_type=event.event_type,
                            error=str(exc),
                        )
                        await asyncio.sleep(0.05 * (2**retry_idx))
            if not persisted:
                self._failed_count += 1
                logger.error(
                    "Exhausted retries persisting event to database",
                    event_type=event.event_type,
                    error=self._last_error,
                )
            self._queue.task_done()

    async def _persist_event(self, event: BaseEvent) -> None:
        """Insert event record into the appropriate ORM table."""
        async with self.session_factory() as session, session.begin():
            try:
                raw_payload = event.model_dump()
            except Exception:
                raw_payload = event.__dict__

            event_record = Event(
                event_type=event.event_type,
                source=event.station_id,
                payload=_sanitize_for_json(raw_payload),
            )
            session.add(event_record)

            # 2. Specialty tables for specific events
            if isinstance(event, AlertRaised):
                alert_record = Alert(
                    subsystem=event.subsystem,
                    severity=event.severity,
                    code=event.code,
                    message=event.message,
                    payload=_sanitize_for_json(event.payload),
                )
                session.add(alert_record)
            elif isinstance(event, HealthChanged):
                health_record = SystemHealth(
                    station_id=event.station_id,
                    subsystem=event.subsystem,
                    status=event.status,
                    telemetry_payload=_sanitize_for_json(event.metrics),
                )
                session.add(health_record)

    async def persist_decision(
        self,
        decision: ProtocolDecision,
        experiment_id: str,
        run_id: str,
    ) -> None:
        """Persist a ProtocolDecision directly to protocol_decisions table."""
        try:
            async with self.session_factory() as session, session.begin():
                record = ProtocolDecisionModel(
                    decision_id=str(decision.decision_id),
                    experiment_id=experiment_id,
                    run_id=run_id,
                    step_id=decision.step_id,
                    step_number=decision.step_number,
                    status=decision.status.value,
                    observed_action=decision.observed_action,
                    expected_actions=decision.expected_actions,
                    confidence=decision.confidence,
                    entropy=decision.entropy,
                    debounce_count=decision.debounce_count,
                    debounce_threshold=decision.debounce_threshold,
                    explanation=decision.explanation,
                    evidence=decision.evidence.model_dump(mode="json"),
                    retroactive_skips=decision.retroactive_skip_step_ids,
                )
                session.add(record)
        except Exception as exc:
            logger.error(
                "Failed to persist protocol decision",
                decision_id=str(decision.decision_id),
                error=str(exc),
            )

    def get_health_report(self) -> SubsystemReport:
        """Produce standardized subsystem health diagnostic report."""
        now = datetime.now(UTC)
        if not self._is_running:
            status = SubsystemStatus.OFFLINE
            err = "Persistence subscriber worker stopped"
        elif self._failed_count > 0 and self._failed_count >= self._persisted_count:
            status = SubsystemStatus.ERROR
            err = f"Sustained persistence failures: {self._last_error}"
        elif self._failed_count > 0:
            status = SubsystemStatus.DEGRADED
            err = f"Experienced persistence failures ({self._failed_count}): {self._last_error}"
        elif self._queue.qsize() > 750:
            status = SubsystemStatus.DEGRADED
            err = f"Persistence queue backlog high: {self._queue.qsize()} events"
        else:
            status = SubsystemStatus.HEALTHY
            err = None

        return SubsystemReport(
            subsystem_id="persistence",
            status=status,
            timestamp=now,
            last_success=self._last_success_utc,
            latency_ms=0.0,
            metrics={
                "persisted_count": self._persisted_count,
                "failed_count": self._failed_count,
                "queue_depth": self._queue.qsize(),
                "queue_capacity": self._queue.maxsize,
            },
            details={
                "worker_running": self._is_running,
            },
            error_message=err,
        )
