"""REST API router for BAS experiment lifecycle, protocol management, and guidance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from orion.core.auth import require_operator, require_viewer
from orion.db.models.decision import ProtocolDecisionModel
from orion.di.container import get_db, get_protocol_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from orion.protocol.service import ProtocolService

router = APIRouter(prefix="/experiments", tags=["experiments"])


class LoadProtocolRequest(BaseModel):
    """Request payload for loading an experiment protocol."""

    protocol_path: str = Field(
        default="configs/protocols/bas_crystal_growth_v1.yaml",
        description="Relative or absolute path to the protocol YAML file.",
    )


class StartExperimentRequest(BaseModel):
    """Request payload for initiating an experiment execution run."""

    run_id: str | None = Field(default=None, description="Optional custom run identifier.")
    actor_track_id: int | None = Field(
        default=None,
        description="Optional primary astronaut track ID for multi-person tracking.",
    )


class ControlRequest(BaseModel):
    """Generic control request with optional reason."""

    reason: str = Field(default="Operator command", description="Reason for the control action.")


class ResolveDeviationRequest(BaseModel):
    """Request payload for resolving a deviation state."""

    resolution: str = Field(
        default="PROCEED",
        description="Resolution strategy: 'PROCEED', 'RETRY', or 'ABORT'.",
    )


class SkipStepRequest(BaseModel):
    """Request payload for jumping directly to a step."""

    target_step_id: str = Field(..., description="Target step identifier to jump to.")


@router.get("/status", summary="Get active experiment state and progress")
async def get_experiment_status(
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_viewer),
) -> dict[str, Any]:
    """Retrieve the real-time status of the protocol state machine and active step."""
    return service.get_status_payload()


@router.post("/load", summary="Load protocol specification")
async def load_experiment_protocol(
    request: LoadProtocolRequest,
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Load, validate, and hash an experiment protocol specification."""
    try:
        spec = service.load_protocol_file(request.protocol_path)
        return {
            "status": "LOADED",
            "experiment_id": spec.metadata.experiment_id,
            "title": spec.metadata.title,
            "protocol_hash": spec.protocol_hash,
            "total_steps": len(spec.steps),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to load protocol: {exc}",
        ) from exc


@router.post("/start", summary="Start experiment execution run")
async def start_experiment_run(
    request: StartExperimentRequest,
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Start execution run for the currently loaded experiment protocol."""
    try:
        run_id = service.start_experiment(
            run_id=request.run_id,
            actor_track_id=request.actor_track_id,
        )
        return {
            "status": service.state.value,
            "run_id": run_id,
            "experiment_id": service.experiment_id,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/pause", summary="Pause experiment execution")
async def pause_experiment(
    request: ControlRequest = ControlRequest(),
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Pause the active experiment execution."""
    try:
        service.pause(reason=request.reason)
        return {"status": service.state.value, "reason": request.reason}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/resume", summary="Resume experiment execution")
async def resume_experiment(
    request: ControlRequest = ControlRequest(),
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Resume paused experiment execution."""
    try:
        service.resume(reason=request.reason)
        return {"status": service.state.value, "reason": request.reason}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/abort", summary="Abort experiment execution")
async def abort_experiment(
    request: ControlRequest = ControlRequest(),
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Permanently abort active experiment run."""
    try:
        service.abort(reason=request.reason)
        return {"status": service.state.value, "reason": request.reason}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/resolve", summary="Resolve blocked deviation")
async def resolve_deviation(
    request: ResolveDeviationRequest,
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Resolve an out-of-sequence or timeout deviation block."""
    try:
        service.resolve_blocked(request.resolution)
        return {"status": service.state.value, "resolution": request.resolution}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/skip", summary="Jump directly to step")
async def skip_to_step(
    request: SkipStepRequest,
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Manually jump to a designated step ID."""
    success = service.skip_to_step(request.target_step_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step '{request.target_step_id}' not found in active protocol",
        )
    return {"status": service.state.value, "step_id": request.target_step_id}


@router.get("/recommendation", summary="Get next-step guidance")
async def get_next_step_recommendation(
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_viewer),
) -> dict[str, Any]:
    """Get active next-step recommendation and timing guidance."""
    rec = service._last_recommendation
    if not rec:
        return {"recommendation": None}
    return {"recommendation": rec.model_dump(mode="json")}


@router.get("/decisions", summary="Query decision audit trail")
async def get_decisions(
    run_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_viewer),
) -> dict[str, Any]:
    """Retrieve persisted protocol validation decisions with linked evidence."""
    stmt = select(ProtocolDecisionModel).order_by(desc(ProtocolDecisionModel.created_at))
    if run_id:
        stmt = stmt.where(ProtocolDecisionModel.run_id == run_id)
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    records = result.scalars().all()

    return {
        "count": len(records),
        "limit": limit,
        "offset": offset,
        "decisions": [
            {
                "decision_id": r.decision_id,
                "experiment_id": r.experiment_id,
                "run_id": r.run_id,
                "step_id": r.step_id,
                "step_number": r.step_number,
                "status": r.status,
                "observed_action": r.observed_action,
                "expected_actions": r.expected_actions,
                "confidence": r.confidence,
                "entropy": r.entropy,
                "debounce_count": r.debounce_count,
                "debounce_threshold": r.debounce_threshold,
                "explanation": r.explanation,
                "evidence": r.evidence,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }


class SelectExperimentRequest(BaseModel):
    """Payload to select an experiment suite and variant."""

    experiment_id: str = Field(default="E01", description="Experiment identifier (E01 to E05)")
    variant: str = Field(default="A", description="Variant ('A' or 'B')")


@router.get("/list", summary="List available BAS experiments and variants")
async def list_available_experiments() -> list[dict[str, Any]]:
    """Return all 5 canonical BAS experiments (E01-E05) and their A/B variants."""
    import json
    from pathlib import Path

    idx_file = Path("configs/protocols/experiments_index.json")
    if idx_file.is_file():
        try:
            with idx_file.open() as f:
                data = json.load(f)
            return [
                {
                    "code": code,
                    "experiment_id": v["experiment_id"],
                    "title": v["title"],
                    "step_count": v["step_count"],
                    "protocol_path": v["file"],
                }
                for code, v in data.items()
            ]
        except Exception:
            pass

    return [
        {
            "code": "E01_A",
            "experiment_id": "BAS-EXP-E01-A",
            "title": "E01 Detecting Colour (Variant A: Yellow then Red)",
            "step_count": 4,
            "protocol_path": "configs/protocols/bas_e01_a.yaml",
        },
        {
            "code": "E01_B",
            "experiment_id": "BAS-EXP-E01-B",
            "title": "E01 Detecting Colour (Variant B: Red then Yellow)",
            "step_count": 4,
            "protocol_path": "configs/protocols/bas_e01_b.yaml",
        },
        {
            "code": "E02_A",
            "experiment_id": "BAS-EXP-E02-A",
            "title": "E02 Interchanging the Boxes (Variant A)",
            "step_count": 3,
            "protocol_path": "configs/protocols/bas_e02_a.yaml",
        },
        {
            "code": "E02_B",
            "experiment_id": "BAS-EXP-E02-B",
            "title": "E02 Interchanging the Boxes (Variant B)",
            "step_count": 3,
            "protocol_path": "configs/protocols/bas_e02_b.yaml",
        },
        {
            "code": "E03_A",
            "experiment_id": "BAS-EXP-E03-A",
            "title": "E03 Overlapping the Boxes (Variant A)",
            "step_count": 2,
            "protocol_path": "configs/protocols/bas_e03_a.yaml",
        },
        {
            "code": "E03_B",
            "experiment_id": "BAS-EXP-E03-B",
            "title": "E03 Overlapping the Boxes (Variant B)",
            "step_count": 2,
            "protocol_path": "configs/protocols/bas_e03_b.yaml",
        },
        {
            "code": "E04_A",
            "experiment_id": "BAS-EXP-E04-A",
            "title": "E04 Moving (Variant A)",
            "step_count": 2,
            "protocol_path": "configs/protocols/bas_e04_a.yaml",
        },
        {
            "code": "E04_B",
            "experiment_id": "BAS-EXP-E04-B",
            "title": "E04 Moving (Variant B)",
            "step_count": 2,
            "protocol_path": "configs/protocols/bas_e04_b.yaml",
        },
        {
            "code": "E05_A",
            "experiment_id": "BAS-EXP-E05-A",
            "title": "E05 In Container (Variant A)",
            "step_count": 4,
            "protocol_path": "configs/protocols/bas_e05_a.yaml",
        },
        {
            "code": "E05_B",
            "experiment_id": "BAS-EXP-E05-B",
            "title": "E05 In Container (Variant B)",
            "step_count": 4,
            "protocol_path": "configs/protocols/bas_e05_b.yaml",
        },
    ]


@router.post("/select", summary="Select and load experiment by ID and variant")
async def select_experiment(
    request: SelectExperimentRequest,
    service: ProtocolService = Depends(get_protocol_service),
    _user: Any = Depends(require_operator),
) -> dict[str, Any]:
    """Dynamically load and activate the designated experiment protocol."""
    code = f"{request.experiment_id.upper()}_{request.variant.upper()}"
    filename = f"bas_{code.lower()}.yaml"
    path = f"configs/protocols/{filename}"

    try:
        spec = service.load_protocol_file(path)
        return {
            "status": "LOADED",
            "code": code,
            "experiment_id": spec.metadata.experiment_id,
            "title": spec.metadata.title,
            "total_steps": len(spec.steps),
            "protocol_hash": spec.protocol_hash,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to load experiment {code}: {exc}",
        ) from exc


@router.get("/summary", summary="Get structured lightweight experiment result log")
async def get_experiment_summary(
    service: ProtocolService = Depends(get_protocol_service),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_viewer),
) -> dict[str, Any]:
    """Generate structured summary of current or most recent experiment run."""
    run_id = service.run_id or "RUN_OFFLINE_LATEST"
    fsm_state = service.state.value

    # Count decisions & violations
    stmt = select(ProtocolDecisionModel).where(ProtocolDecisionModel.run_id == run_id)
    res = await db.execute(stmt)
    records = res.scalars().all()

    violations = [
        r
        for r in records
        if r.status
        in (
            "OUT_OF_SEQUENCE",
            "SKIPPED",
            "WRONG_OBJECT",
            "INTERRUPTED",
            "TIMEOUT",
            "INVALID_ACTION",
        )
    ]

    total_steps = len(service.fsm.spec.steps) if service.fsm.spec else 0
    current_step_num = (
        service.fsm.current_step.step_number if service.fsm.current_step else total_steps
    )
    steps_completed = total_steps if fsm_state == "COMPLETED" else max(0, current_step_num - 1)

    return {
        "experiment_id": service.experiment_id,
        "run_id": run_id,
        "fsm_state": fsm_state,
        "status": "COMPLETED"
        if (fsm_state == "COMPLETED" and len(violations) == 0)
        else ("VIOLATION" if len(violations) > 0 else fsm_state),
        "steps_completed": steps_completed,
        "total_steps": total_steps,
        "total_decisions": len(records),
        "total_violations": len(violations),
        "violations": [
            {
                "decision_id": str(v.decision_id),
                "step_id": v.step_id,
                "status": v.status,
                "observed_action": v.observed_action,
                "expected_actions": v.expected_actions,
                "confidence": v.confidence,
                "explanation": v.explanation,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in violations
        ],
        "ai_model": "BAS-HAR-v1.0",
        "dataset_version": "BAS-DATA-v1.0.0",
    }
