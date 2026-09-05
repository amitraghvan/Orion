"""Model registry configuration schemas."""

from pydantic import BaseModel


class ModelRegistryConfig(BaseModel):
    """Configuration contract for model storage and certification policy."""

    storage_root: str = "./models/weights"
    enforce_sha256: bool = True
    require_flight_certification: bool = False
