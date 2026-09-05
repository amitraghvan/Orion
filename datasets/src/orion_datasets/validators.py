"""Dataset quality assurance and verification interfaces."""

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field


class DatasetQualityReport(BaseModel):
    """Quality assessment output for scientific flight datasets."""

    total_samples_audited: int
    corrupted_images: list[str] = Field(default_factory=list)
    blurry_images: list[str] = Field(default_factory=list)
    missing_annotation_samples: list[str] = Field(default_factory=list)
    zero_area_boxes: int = 0
    passed_quality_gate: bool = False


class DatasetQualityAuditorInterface(ABC):
    """Interface for verifying dataset integrity before training."""

    @abstractmethod
    def audit_quality(self, dataset_dir: Path) -> DatasetQualityReport:
        """Inspect all images and annotations for corrupted headers, blur, or missing labels."""
        raise NotImplementedError("NOT IMPLEMENTED: DatasetQualityAuditorInterface.audit_quality")
