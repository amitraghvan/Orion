"""Runtime configuration schemas."""

from pydantic import BaseModel, Field


class RuntimeConfig(BaseModel):
    """Configuration contract for perception runtime pipeline."""

    pipeline_mode: str = "sequential"  # sequential, parallel, pipelined
    enable_drop_on_lag: bool = True
    max_queue_depth: int = Field(default=3, ge=1)
    target_fps: int = Field(default=30, ge=1)
