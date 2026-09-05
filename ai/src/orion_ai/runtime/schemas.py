"""Perception runtime and scheduling schemas."""

from pydantic import BaseModel, Field


class ExecutionContext(BaseModel):
    """Runtime execution parameters for a perception pass."""

    session_id: str
    frame_index: int
    timestamp_sensor_ns: int
    active_models: list[str]
    max_latency_budget_ms: float = 33.3  # 30 FPS budget


class PipelineTask(BaseModel):
    """Individual perception task within the execution DAG."""

    task_id: str
    task_type: str  # detection, pose, tracking, activity, state_machine
    dependencies: list[str] = Field(default_factory=list)
    priority: int = 0


class RuntimePerformance(BaseModel):
    """Execution telemetry for a completed perception cycle."""

    frame_index: int
    total_cycle_ms: float
    breakdown_ms: dict[str, float]
    dropped_frames: int = 0
    gpu_memory_used_mb: float = 0.0
