from __future__ import annotations

import asyncio
import contextlib
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from experiments.loader import load_protocol

from orion.core.logger import get_logger
from orion.events.schemas import (
    ActivityRecognized,
    ExperimentUpdated,
    NextStepRecommended,
    ObservationCaptured,
    ProtocolDeviationDetected,
    ProtocolStateChanged,
    StepTransitioned,
)
from orion.health.interfaces import SubsystemReport, SubsystemStatus
from orion.protocol.action_mapping import ActivityToActionMapper
from orion.protocol.decision_engine import (
    DecisionStatus,
    ProtocolDecision,
    ProtocolDecisionEngine,
)
from orion.protocol.next_step_engine import (
    NextStepGuidanceEngine,
    NextStepRecommendation,
)
from orion.protocol.state_machine import (
    ProtocolState,
    ProtocolStateMachine,
)

if TYPE_CHECKING:
    from pathlib import Path

    from experiments.schemas import ExperimentSpecification

    from orion.core.in_memory_event_bus import InMemoryEventBus
    from orion.db.persistence_subscriber import EventPersistenceSubscriber

logger = get_logger("orion.protocol.service")



class ProtocolService:
    """Core protocol coordination service."""

    def __init__(
        self,
        event_bus: InMemoryEventBus | None = None,
        persistence_subscriber: EventPersistenceSubscriber | None = None,
        action_mapper: ActivityToActionMapper | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.persistence_subscriber = persistence_subscriber
        self.mapper = action_mapper or ActivityToActionMapper()
        self.decision_engine = ProtocolDecisionEngine(action_mapper=self.mapper)
        self.fsm = ProtocolStateMachine()
        self.guidance_engine = NextStepGuidanceEngine()

        self._experiment_id: str = ""
        self._current_run_id: str = ""
        self._last_recommendation: NextStepRecommendation | None = None
        self._latest_observation: Any = None
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._last_observation_utc: datetime | None = None
        self._last_decision_utc: datetime | None = None
        self._last_error: str | None = None

        # Subscribe to ActivityRecognized and ObservationCaptured if event_bus is provided
        if self.event_bus:
            self.event_bus.subscribe(ActivityRecognized, self.on_activity_recognized)
            self.event_bus.subscribe(ObservationCaptured, self.on_observation_captured)

    @property
    def experiment_id(self) -> str:
        return self._experiment_id

    @property
    def run_id(self) -> str:
        return self._current_run_id

    @property
    def state(self) -> ProtocolState:
        return self.fsm.state

    @property
    def current_recommendation(self) -> NextStepRecommendation | None:
        return self._last_recommendation

    def load_protocol_file(self, protocol_path: str | Path) -> ExperimentSpecification:
        """Load protocol from file, initialize FSM and decision engine."""
        spec = load_protocol(protocol_path)
        self.fsm.load_protocol(spec)
        self._experiment_id = spec.metadata.experiment_id
        self._current_run_id = ""
        self.decision_engine.reset_step()
        self._last_recommendation = self.guidance_engine.compute_recommendation(self.fsm)

        logger.info(
            "Protocol loaded successfully",
            experiment_id=self._experiment_id,
            protocol_hash=spec.protocol_hash,
            steps_count=len(spec.steps),
        )
        return spec

    def start_experiment(
        self,
        run_id: str | None = None,
        actor_track_id: int | None = None,
    ) -> str:
        """Begin experiment execution run."""
        if not self.fsm.spec:
            raise ValueError("No protocol loaded. Load a protocol first.")

        assigned_run_id = run_id or f"run_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self._current_run_id = assigned_run_id
        prev_state = self.fsm.state

        self.fsm.start_run(assigned_run_id, actor_track_id=actor_track_id)
        self.decision_engine.reset_step()
        self._last_recommendation = self.guidance_engine.compute_recommendation(self.fsm)

        self._emit_state_change(prev_state.value, self.fsm.state.value, reason="Experiment run started")
        return assigned_run_id

    def pause(self, reason: str = "Operator paused") -> None:
        """Pause active experiment."""
        prev_state = self.fsm.state
        self.fsm.pause(reason=reason)
        self._last_recommendation = self.guidance_engine.compute_recommendation(self.fsm)
        self._emit_state_change(prev_state.value, self.fsm.state.value, reason=reason)

    def resume(self, reason: str = "Operator resumed") -> None:
        """Resume active experiment."""
        prev_state = self.fsm.state
        self.fsm.resume(reason=reason)
        self._last_recommendation = self.guidance_engine.compute_recommendation(self.fsm)
        self._emit_state_change(prev_state.value, self.fsm.state.value, reason=reason)

    def abort(self, reason: str = "Operator aborted") -> None:
        """Abort active experiment."""
        prev_state = self.fsm.state
        self.fsm.abort(reason=reason)
        self._last_recommendation = self.guidance_engine.compute_recommendation(self.fsm)
        self._emit_state_change(prev_state.value, self.fsm.state.value, reason=reason)

    def resolve_blocked(self, resolution: str) -> None:
        """Resolve deviation state."""
        prev_state = self.fsm.state
        self.fsm.resolve_blocked(resolution)
        self.decision_engine.reset_step()
        self._last_recommendation = self.guidance_engine.compute_recommendation(self.fsm)
        self._emit_state_change(prev_state.value, self.fsm.state.value, reason=f"Resolved: {resolution}")

    def skip_to_step(self, target_step_id: str) -> bool:
        """Manually jump to a designated step by ID."""
        prev_state = self.fsm.state
        success = self.fsm.skip_to_step(target_step_id)
        if success:
            self.decision_engine.reset_step()
            self._last_recommendation = self.guidance_engine.compute_recommendation(self.fsm)
            self._emit_state_change(prev_state.value, self.fsm.state.value, reason=f"Manual jump to {target_step_id}")
        return success

    async def on_activity_recognized(self, event: ActivityRecognized) -> None:
        """Callback invoked when ActivityRecognized event is received from event bus."""
        await self.process_activity(event)

    async def on_observation_captured(self, event: ObservationCaptured) -> None:
        """Callback invoked when ObservationCaptured event is received from event bus."""
        self._latest_observation = event.observation
        self._last_observation_utc = event.timestamp
        obs = event.observation
        if not obs or self.fsm.state not in (
            ProtocolState.RUNNING,
            ProtocolState.STEP_IN_PROGRESS,
            ProtocolState.STEP_COMPLETED,
        ):
            return

        act_label: str | None = None
        act_conf: float = 0.0
        track_id: int = 0

        # 1. First priority: Check direct HAR prediction
        if (
            hasattr(obs, "top_activity")
            and obs.top_activity
            and obs.top_activity.activity_name != "idle"
            and obs.top_activity.confidence >= 0.35
        ):
            act_label = obs.top_activity.activity_name
            act_conf = obs.top_activity.confidence
            track_id = obs.activities[0].track_id if obs.activities else 0

        # 2. Second priority: If HAR is idle or low confidence, check physical Hand-Object Interactions
        if not act_label and hasattr(obs, "interaction_observations") and obs.interaction_observations:
            for inter in obs.interaction_observations:
                state_val = getattr(inter.state, "value", str(inter.state))
                if state_val in ("CONTACT", "GRASPING", "MANIPULATING"):
                    obj_id = str(getattr(inter, "object_id", "")).lower()
                    current_step = self.fsm.current_step
                    expected_act = current_step.expected_activity if current_step else ""
                    if "yellow" in obj_id:
                        act_label = "place_yellow" if "place" in expected_act else "pick_yellow"
                        act_conf = 0.92
                        track_id = getattr(inter, "person_track_id", 0)
                        break
                    elif "red" in obj_id:
                        act_label = "place_red" if "place" in expected_act else "pick_red"
                        act_conf = 0.92
                        track_id = getattr(inter, "person_track_id", 0)
                        break

        if act_label and act_conf >= 0.3:
            act_event = ActivityRecognized(
                station_id=event.station_id,
                track_id=track_id,
                frame_index=obs.frame_index,
                window_start_frame=max(0, obs.frame_index - 32),
                window_end_frame=obs.frame_index,
                activity_label=act_label,
                phase="UPDATE",
                confidence=act_conf,
                uncertainty_status="NOMINAL",
                is_anomaly=False,
                model_version=getattr(obs.top_activity, "model_version", "BAS-HAR-v1.0") if getattr(obs, "top_activity", None) else "BAS-HOI-v1.0",
                evidence_metadata={
                    "source": "observation_stream",
                    "inferred_from": "hoi" if not getattr(obs, "top_activity", None) else "har",
                },
            )
            await self.process_activity(act_event)


    async def process_activity(
        self,
        event: ActivityRecognized,
        now: datetime | None = None,
    ) -> ProtocolDecision | None:
        """Process an activity recognition event through decision engine and state machine."""
        if not self.fsm.spec or self.fsm.state not in (
            ProtocolState.RUNNING,
            ProtocolState.STEP_IN_PROGRESS,
            ProtocolState.STEP_COMPLETED,
        ):
            return None

        # Multi-person actor tracking filter
        if self.fsm.actor_track_id is not None and event.track_id not in (0, self.fsm.actor_track_id):
            logger.debug(
                "Ignoring activity from non-primary actor",
                event_track=event.track_id,
                primary_actor=self.fsm.actor_track_id,
            )
            return None

        prev_state = self.fsm.state
        prev_step = self.fsm.current_step

        try:
            decision = self.decision_engine.evaluate(
                event=event,
                spec=self.fsm.spec,
                current_step_index=self.fsm.current_step_index,
                now=now,
            )
            self._last_decision_utc = datetime.now(UTC)
            self._last_error = None
        except Exception as exc:
            self._last_error = str(exc)
            logger.error("Protocol decision evaluation exception", error=str(exc))
            self.fsm.mark_degraded(str(exc))
            self._emit_state_change(prev_state.value, ProtocolState.DEGRADED.value, reason=str(exc))
            return None

        # Mutate FSM
        self.fsm.process_decision(decision)

        # Check if step advanced
        current_step = self.fsm.current_step
        if prev_step and current_step and prev_step.step_id != current_step.step_id:
            self.decision_engine.reset_step(now)
            if self.event_bus:
                await self.event_bus.publish(
                    StepTransitioned(
                        experiment_id=self._experiment_id,
                        run_id=self._current_run_id,
                        from_step_id=prev_step.step_id,
                        to_step_id=current_step.step_id,
                        from_step_number=prev_step.step_number,
                        to_step_number=current_step.step_number,
                        duration_seconds=0.0,
                        decision_id=str(decision.decision_id),
                    )
                )

        # Check if deviation occurred
        if (
            decision.status
            in (
                DecisionStatus.OUT_OF_SEQUENCE,
                DecisionStatus.SKIPPED,
                DecisionStatus.WRONG_OBJECT,
                DecisionStatus.INTERRUPTED,
                DecisionStatus.TIMEOUT,
                DecisionStatus.INVALID_ACTION,
            )
            and self.event_bus
            and prev_step
        ):
            from orion.events.schemas import AlertRaised
            await self.event_bus.publish(
                ProtocolDeviationDetected(
                    experiment_id=self._experiment_id,
                    run_id=self._current_run_id,
                    step_id=prev_step.step_id,
                    step_number=prev_step.step_number,
                    deviation_type=decision.status.value,
                    observed_action=decision.observed_action,
                    expected_actions=decision.expected_actions,
                    confidence=decision.confidence,
                    entropy=decision.entropy,
                    message=decision.explanation,
                    decision_id=str(decision.decision_id),
                )
            )
            spoken_alert = (
                f"Protocol violation: {decision.status.value.replace('_', ' ').title()}. "
                f"Expected {', '.join(decision.expected_actions)}, observed {decision.observed_action}."
            )
            await self.event_bus.publish(
                AlertRaised(
                    station_id="BAS-NODE-01",
                    subsystem="ProtocolEngine",
                    severity="WARNING",
                    code=f"PROTOCOL_{decision.status.value}",
                    message=decision.explanation,
                    payload={
                        "experiment_id": self._experiment_id,
                        "deviation_type": decision.status.value,
                        "observed": decision.observed_action,
                        "expected": decision.expected_actions,
                        "confidence": decision.confidence,
                        "spoken_message": spoken_alert,
                    },
                )
            )

        # Check state change
        if prev_state != self.fsm.state:
            self._emit_state_change(
                prev_state.value,
                self.fsm.state.value,
                reason=decision.explanation,
            )

        # Compute next recommendation
        self._last_recommendation = self.guidance_engine.compute_recommendation(self.fsm, now=now)
        if self.event_bus and self._last_recommendation:
            await self.event_bus.publish(
                NextStepRecommended(
                    experiment_id=self._experiment_id,
                    run_id=self._current_run_id,
                    step_id=self._last_recommendation.step_id,
                    step_number=self._last_recommendation.step_number,
                    expected_activity=self._last_recommendation.expected_activity,
                    instruction_text=self._last_recommendation.instruction_text,
                    remaining_nominal_seconds=self._last_recommendation.remaining_nominal_seconds,
                )
            )

        # Persist decision to SQLite audit table
        if self.persistence_subscriber:
            await self.persistence_subscriber.persist_decision(
                decision=decision,
                experiment_id=self._experiment_id,
                run_id=self._current_run_id,
            )

        return decision

    def _emit_state_change(self, from_state: str, to_state: str, reason: str = "") -> None:
        """Publish ProtocolStateChanged and ExperimentUpdated events."""
        if not self.event_bus:
            return

        step = self.fsm.current_step
        # Asynchronously schedule publication
        event = ProtocolStateChanged(
            experiment_id=self._experiment_id,
            run_id=self._current_run_id,
            from_state=from_state,
            to_state=to_state,
            step_id=step.step_id if step else None,
            step_number=step.step_number if step else None,
            reason=reason,
        )

        status_mapping = {
            ProtocolState.IDLE: "PENDING",
            ProtocolState.LOADED: "PENDING",
            ProtocolState.PRECHECK: "PENDING",
            ProtocolState.RUNNING: "RUNNING",
            ProtocolState.STEP_IN_PROGRESS: "RUNNING",
            ProtocolState.STEP_COMPLETED: "RUNNING",
            ProtocolState.PAUSED: "PAUSED",
            ProtocolState.BLOCKED: "RUNNING",
            ProtocolState.COMPLETED: "COMPLETED",
            ProtocolState.ABORTED: "ABORTED",
            ProtocolState.DEGRADED: "FAILED",
        }
        mapped_status = status_mapping.get(self.fsm.state, "RUNNING")

        updated_event = ExperimentUpdated(
            experiment_id=self._experiment_id or "NONE",
            run_id=self._current_run_id or "NONE",
            previous_step_id=None,
            current_step_id=step.step_id if step else "NONE",
            status=mapped_status,  # type: ignore[arg-type]
        )

        # Fire and forget if loop is running
        with contextlib.suppress(RuntimeError):
            loop = asyncio.get_running_loop()
            t1 = loop.create_task(self.event_bus.publish(event))
            self._background_tasks.add(t1)
            t1.add_done_callback(self._background_tasks.discard)

            t2 = loop.create_task(self.event_bus.publish(updated_event))
            self._background_tasks.add(t2)
            t2.add_done_callback(self._background_tasks.discard)


    def get_status_payload(self) -> dict[str, Any]:
        """Produce complete telemetry / REST status payload."""
        step = self.fsm.current_step
        spec = self.fsm.spec
        recommendation = self._last_recommendation.model_dump(mode="json") if self._last_recommendation else None

        steps_summary = []
        if spec:
            for idx, s in enumerate(spec.steps):
                if idx < self.fsm.current_step_index:
                    step_st = "COMPLETED"
                elif idx == self.fsm.current_step_index:
                    if self.fsm.state in (
                        ProtocolState.RUNNING,
                        ProtocolState.STEP_IN_PROGRESS,
                        ProtocolState.STEP_COMPLETED,
                    ):
                        step_st = "ACTIVE"
                    elif self.fsm.state == ProtocolState.ABORTED:
                        step_st = "ABORTED"
                    elif self.fsm.state == ProtocolState.PAUSED:
                        step_st = "PAUSED"
                    elif self.fsm.state == ProtocolState.COMPLETED:
                        step_st = "COMPLETED"
                    else:
                        step_st = "PENDING"
                else:
                    step_st = "PENDING"
                steps_summary.append({
                    "step_id": s.step_id,
                    "step_number": s.step_number,
                    "description": s.description,
                    "expected_activity": s.expected_activity,
                    "status": step_st,
                })

        return {
            "experiment_id": self._experiment_id,
            "run_id": self._current_run_id,
            "fsm_state": self.fsm.state.value,
            "protocol_hash": spec.protocol_hash if spec else None,
            "total_steps": len(spec.steps) if spec else 0,
            "current_step_index": self.fsm.current_step_index,
            "current_step": {
                "step_id": step.step_id,
                "step_number": step.step_number,
                "description": step.description,
                "expected_activity": step.expected_activity,
            } if step else None,
            "recommendation": recommendation,
            "steps": steps_summary,
            "actor_track_id": self.fsm.actor_track_id,
        }

    def get_health_report(self) -> SubsystemReport:
        """Produce structured subsystem health diagnostic report."""
        now = datetime.now(UTC)
        if self.fsm.state == ProtocolState.DEGRADED:
            status = SubsystemStatus.DEGRADED
            err = self._last_error or "Protocol FSM in degraded state"
        elif self._last_error:
            status = SubsystemStatus.DEGRADED
            err = f"Protocol evaluation warning: {self._last_error}"
        else:
            status = SubsystemStatus.HEALTHY
            err = None

        step = self.fsm.current_step
        return SubsystemReport(
            subsystem_id="protocol",
            status=status,
            timestamp=now,
            last_success=self._last_decision_utc or self._last_observation_utc,
            latency_ms=0.0,
            metrics={
                "current_step_index": self.fsm.current_step_index,
                "total_steps": len(self.fsm.spec.steps) if self.fsm.spec else 0,
            },
            details={
                "experiment_id": self._experiment_id,
                "run_id": self._current_run_id,
                "fsm_state": self.fsm.state.value,
                "current_step_id": step.step_id if step else None,
            },
            error_message=err,
        )
