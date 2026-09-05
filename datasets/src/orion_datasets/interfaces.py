"""Dataset loader, converter, and split interfaces."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class DatasetLoaderInterface(ABC):
    """Abstract contract for loading multi-format annotations."""

    @abstractmethod
    def load(self, annotation_file: Path) -> Any:
        """Parse annotation file into structured memory schema."""
        raise NotImplementedError("NOT IMPLEMENTED: DatasetLoaderInterface.load")


class DatasetConverterInterface(ABC):
    """Abstract contract for format cross-compilation (e.g. CVAT -> COCO / YOLO)."""

    @abstractmethod
    def convert(self, source_path: Path, output_path: Path, target_format: str) -> Path:
        """Convert dataset annotations to target format."""
        raise NotImplementedError("NOT IMPLEMENTED: DatasetConverterInterface.convert")


class DatasetSplitterInterface(ABC):
    """Abstract contract for deterministic split generation."""

    @abstractmethod
    def split(
        self, dataset_path: Path, train_ratio: float, val_ratio: float, test_ratio: float, seed: int
    ) -> dict[str, list[str]]:
        """Compute train/val/test splits maintaining class stratification."""
        raise NotImplementedError("NOT IMPLEMENTED: DatasetSplitterInterface.split")
