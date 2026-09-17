"""Data access repositories for experiment runs, steps, and system logs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.database.database import db_manager
from app.database.models import (
    ExperimentModel,
    ExperimentRunModel,
    ExperimentStepLogModel,
)


class ExperimentRepository:
    """Handles CRUD persistence for mission experiments and execution sessions."""

    def record_run_start(
        self, experiment_id: str, run_id: str, title: str, total_steps: int
    ) -> None:
        session = db_manager.get_session()
        try:
            # Ensure experiment exists
            exp = session.query(ExperimentModel).filter_by(experiment_id=experiment_id).first()
            if not exp:
                exp = ExperimentModel(experiment_id=experiment_id, title=title)
                session.add(exp)

            run = ExperimentRunModel(
                run_id=run_id,
                experiment_id=experiment_id,
                status="RUNNING",
                start_time=datetime.now(UTC),
                total_steps=total_steps,
            )
            session.add(run)
            session.commit()
        finally:
            session.close()

    def record_step_execution(
        self,
        run_id: str,
        step_number: int,
        step_id: str,
        expected_action: str,
        detected_action: str,
        status: str,
        confidence: float,
        explanation: str,
    ) -> None:
        session = db_manager.get_session()
        try:
            step_log = ExperimentStepLogModel(
                run_id=run_id,
                step_number=step_number,
                step_id=step_id,
                expected_action=expected_action,
                detected_action=detected_action,
                status=status,
                confidence=confidence,
                explanation=explanation,
            )
            session.add(step_log)

            run = session.query(ExperimentRunModel).filter_by(run_id=run_id).first()
            if run:
                if status == "VALID":
                    run.completed_steps += 1
                elif status in ("OUT_OF_SEQUENCE", "SKIPPED", "WRONG_OBJECT"):
                    run.violations_count += 1
            session.commit()
        finally:
            session.close()

    def finalize_run(self, run_id: str, status: str = "COMPLETED", duration_s: float = 0.0) -> None:
        session = db_manager.get_session()
        try:
            run = session.query(ExperimentRunModel).filter_by(run_id=run_id).first()
            if run:
                run.status = status
                run.end_time = datetime.now(UTC)
                run.duration_seconds = duration_s
                session.commit()
        finally:
            session.close()

    def list_all_runs(self) -> list[dict[str, Any]]:
        session = db_manager.get_session()
        try:
            runs = (
                session.query(ExperimentRunModel)
                .order_by(ExperimentRunModel.start_time.desc())
                .limit(50)
                .all()
            )
            return [
                {
                    "run_id": r.run_id,
                    "experiment_id": r.experiment_id,
                    "status": r.status,
                    "start_time": r.start_time.strftime("%Y-%m-%d %H:%M:%S")
                    if r.start_time
                    else "",
                    "duration_seconds": round(r.duration_seconds, 1),
                    "completed_steps": r.completed_steps,
                    "total_steps": r.total_steps,
                    "violations": r.violations_count,
                }
                for r in runs
            ]
        finally:
            session.close()


experiment_repo = ExperimentRepository()
