"""Central experiment coordinator evaluating real-time observations against protocols."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.config import get_config
from app.core.event_bus import event_bus
from app.core.logging import get_logger
from app.core.state_manager import state_manager
from app.experiments.experiment_loader import load_protocol
from app.experiments.experiment_schema import ExperimentSpecification
from app.experiments.sequence_manager import ProtocolState, ProtocolStateMachine
from app.intelligence.decision_engine import DecisionStatus, ProtocolDecision, ProtocolDecisionEngine
from app.intelligence.next_step_engine import NextStepEngine, NextStepRecommendation

logger = get_logger("app.experiments.engine")


class ExperimentEngine:
    """Manages experiment lifecycles, observation routing, step validation, and alert dispatch."""

    def __init__(self) -> None:
        self.fsm = ProtocolStateMachine()
        self.decision_engine = ProtocolDecisionEngine()
        self.next_step_engine = NextStepEngine()

        self._active_run_id: str = ""
        self._active_protocol_path: str = ""
        self._timeline_events: list[dict[str, Any]] = []
        self._step_records: list[dict[str, Any]] = []
        self._start_time_str: str = ""
        self._start_mono: float = 0.0
        self._lock = threading.RLock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self.fsm.state in (ProtocolState.RUNNING, ProtocolState.STEP_IN_PROGRESS)

    @property
    def current_spec(self) -> ExperimentSpecification | None:
        with self._lock:
            return self.fsm.spec

    def load_protocol_file(self, file_path: str) -> ExperimentSpecification:
        """Load experiment specification from YAML file."""
        with self._lock:
            spec = load_protocol(file_path)
            self._active_protocol_path = file_path
            self.fsm.load_spec(spec)
            self.decision_engine.reset_step()

            # Update state manager
            curr_step = self.fsm.current_step
            state_manager.set_experiment_status(
                experiment_id=spec.metadata.experiment_id,
                run_id=self._active_run_id,
                fsm_state=self.fsm.state.value,
                step_number=curr_step.step_number if curr_step else 1,
                step_id=curr_step.step_id if curr_step else "",
                step_name=curr_step.description if curr_step else "",
                total_steps=len(spec.steps),
                expected_action=curr_step.expected_actions[0] if curr_step and curr_step.expected_actions else "execute",
            )

            # Update guidance
            guidance = self.next_step_engine.compute_guidance(spec, 0)
            state_manager.set_guidance(
                next_step_text=guidance.instruction_text,
                next_step_action=guidance.expected_action,
            )

            logger.info("Loaded protocol successfully", exp_id=spec.metadata.experiment_id, steps=len(spec.steps))
            return spec

    def start_experiment(self) -> str:
        """Start mission run for currently loaded protocol."""
        with self._lock:
            if not self.fsm.spec:
                raise ValueError("Cannot start experiment: No protocol loaded.")

            self._active_run_id = f"RUN-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6].upper()}"
            self._start_time_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            self._start_mono = time.monotonic()
            self._timeline_events.clear()
            self._step_records.clear()

            self.fsm.start_execution()
            self.decision_engine.reset_step()

            # Start asynchronous session video recording
            from app.recording.recorder import experiment_recorder
            cfg = get_config()
            experiment_recorder.start_recording(
                experiment_id=self.fsm.spec.metadata.experiment_id,
                run_id=self._active_run_id,
                width=cfg.camera.width,
                height=cfg.camera.height,
                fps=cfg.camera.fps,
            )

            self._log_timeline("EXPERIMENT_STARTED", f"Run {self._active_run_id} started for {self.fsm.spec.metadata.experiment_id}")

            curr_step = self.fsm.current_step
            state_manager.set_experiment_status(
                experiment_id=self.fsm.spec.metadata.experiment_id,
                run_id=self._active_run_id,
                fsm_state=self.fsm.state.value,
                step_number=curr_step.step_number if curr_step else 1,
                step_id=curr_step.step_id if curr_step else "",
                step_name=curr_step.description if curr_step else "",
                total_steps=len(self.fsm.spec.steps),
                expected_action=curr_step.expected_actions[0] if curr_step and curr_step.expected_actions else "execute",
            )

            guidance = self.next_step_engine.compute_guidance(self.fsm.spec, 0)
            state_manager.set_guidance(guidance.instruction_text, guidance.expected_action)

            # Trigger voice notification
            event_bus.publish({
                "type": "VOICE_ALERT",
                "text": "Experiment started. Please perform Step 1.",
                "priority": 3,
            })

            return self._active_run_id

    def process_observation(self, activity_label: str, confidence: float, entropy: float) -> ProtocolDecision | None:
        """Evaluate incoming HAR action observation against the active experiment step."""
        with self._lock:
            if not self.is_running or not self.fsm.spec:
                return None

            current_idx = self.fsm.current_step_index
            decision = self.decision_engine.evaluate(
                observed_activity=activity_label,
                confidence=confidence,
                entropy=entropy,
                spec=self.fsm.spec,
                current_step_index=current_idx,
            )

            # Update decision status in state manager
            state_manager.set_decision_status(
                detected_action=decision.observed_action,
                confidence=decision.confidence,
                sequence_status=decision.status.value,
            )

            # Collect significant decision events for session log
            if decision.status in (
                DecisionStatus.VALID,
                DecisionStatus.OUT_OF_SEQUENCE,
                DecisionStatus.WRONG_OBJECT,
                DecisionStatus.SKIPPED,
                DecisionStatus.INVALID_ACTION,
            ):
                self._step_records.append({
                    "step_number": decision.step_number,
                    "step_id": decision.step_id,
                    "expected_action": decision.expected_actions[0] if decision.expected_actions else "execute",
                    "detected_action": decision.observed_action,
                    "status": decision.status.value,
                    "confidence": float(decision.confidence),
                    "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "explanation": decision.explanation,
                })

            # Handle Decision Outcomes
            if decision.status == DecisionStatus.VALID:
                curr_num = decision.step_number
                self._log_timeline(f"STEP_{curr_num:02d}_COMPLETED", f"Validated action '{decision.observed_action}' (conf={decision.confidence:.2f})")

                # Advance FSM
                is_complete = self.fsm.advance_step()
                self.decision_engine.reset_step()

                if is_complete:
                    self._log_timeline("EXPERIMENT_COMPLETED", "All experiment protocol steps finalized successfully.")
                    event_bus.publish({
                        "type": "VOICE_ALERT",
                        "text": "Experiment completed successfully. All steps verified.",
                        "priority": 2,
                    })
                    self._finalize_mission(outcome="COMPLETED")
                else:
                    nxt_step = self.fsm.current_step
                    event_bus.publish({
                        "type": "VOICE_ALERT",
                        "text": f"Step {curr_num} completed. Please perform Step {nxt_step.step_number if nxt_step else curr_num + 1}.",
                        "priority": 3,
                    })

                # Refresh state & guidance
                new_step = self.fsm.current_step
                state_manager.set_experiment_status(
                    experiment_id=self.fsm.spec.metadata.experiment_id,
                    run_id=self._active_run_id,
                    fsm_state=self.fsm.state.value,
                    step_number=new_step.step_number if new_step else len(self.fsm.spec.steps),
                    step_id=new_step.step_id if new_step else "COMPLETED",
                    step_name=new_step.description if new_step else "Mission Complete",
                    total_steps=len(self.fsm.spec.steps),
                    expected_action=new_step.expected_actions[0] if new_step and new_step.expected_actions else "idle",
                )

                guidance = self.next_step_engine.compute_guidance(self.fsm.spec, self.fsm.current_step_index)
                state_manager.set_guidance(guidance.instruction_text, guidance.expected_action)

            elif decision.status == DecisionStatus.OUT_OF_SEQUENCE:
                self._log_timeline("OUT_OF_SEQUENCE_ACTION", decision.explanation)
                event_bus.publish({
                    "type": "VOICE_ALERT",
                    "text": "Warning. Out of sequence activity detected.",
                    "priority": 1,
                })
                event_bus.publish({
                    "type": "ALERT",
                    "severity": "WARNING",
                    "message": decision.explanation,
                })

            elif decision.status == DecisionStatus.WRONG_OBJECT:
                self._log_timeline("WRONG_OBJECT_VIOLATION", decision.explanation)
                event_bus.publish({
                    "type": "VOICE_ALERT",
                    "text": "Warning. Wrong object manipulated.",
                    "priority": 1,
                })
                event_bus.publish({
                    "type": "ALERT",
                    "severity": "WARNING",
                    "message": decision.explanation,
                })

            elif decision.status == DecisionStatus.SKIPPED:
                self._log_timeline("STEP_SKIPPED", decision.explanation)
                event_bus.publish({
                    "type": "VOICE_ALERT",
                    "text": "Alert. Protocol step was skipped.",
                    "priority": 1,
                })

            return decision

    def stop_experiment(self) -> None:
        """Halt active mission run."""
        with self._lock:
            if self.is_running:
                self.fsm.abort(reason="Operator requested halt")
                self._log_timeline("EXPERIMENT_ABORTED", "Experiment execution halted by operator.")
                self._finalize_mission(outcome="ABORTED")
                state_manager.update_telemetry()

    def _finalize_mission(self, outcome: str) -> None:
        """Finalize video recording, flush telemetry events, and generate mission verification reports."""
        import time
        from app.recording.recorder import experiment_recorder
        from app.reports.report_generator import report_generator

        end_time_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        duration = time.monotonic() - self._start_mono if self._start_mono > 0 else 0.0

        # Stop recorder and write session artifacts
        recording_meta = experiment_recorder.stop_recording(
            events=self._step_records,
            timeline=self._timeline_events,
        )

        # Generate scientific Markdown and JSON dossier
        if self.fsm.spec:
            exp_id = self.fsm.spec.metadata.experiment_id
            exp_title = self.fsm.spec.metadata.title
            system_info = {
                "backend": "PyTorch / C++",
                "device": "MPS / CPU",
                "outcome": outcome,
                "recorded_video": recording_meta.get("video_file") if recording_meta else None,
            }
            report_path = report_generator.generate_report(
                experiment_id=exp_id,
                experiment_title=exp_title,
                run_id=self._active_run_id,
                start_time=self._start_time_str,
                end_time=end_time_str,
                duration_seconds=duration,
                steps_log=self._step_records,
                system_info=system_info,
            )
            logger.info("Generated mission verification dossier", report_path=str(report_path))
            event_bus.publish({
                "type": "REPORT_GENERATED",
                "report_path": str(report_path),
                "run_id": self._active_run_id,
                "outcome": outcome,
            })

    def get_timeline(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._timeline_events)

    def _log_timeline(self, event_type: str, details: str) -> None:
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": now_str,
            "type": event_type,
            "details": details,
        }
        self._timeline_events.append(entry)
        logger.info(f"[{now_str}] {event_type} - {details}")


# Global experiment engine singleton
experiment_engine = ExperimentEngine()
