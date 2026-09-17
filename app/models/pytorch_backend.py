"""PyTorch / Ultralytics execution backend for CPU, Apple Silicon (MPS), and NVIDIA CUDA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.exceptions import ModelError
from app.core.logging import get_logger
from app.models.inference_backend import InferenceBackend

logger = get_logger("app.models.pytorch")


class PyTorchBackend(InferenceBackend):
    """Inference backend leveraging native PyTorch and Ultralytics runtime."""

    def __init__(self, model_path: str, device: str = "auto") -> None:
        super().__init__(model_path, device)
        self._model: Any = None
        self._resolved_device: str = "cpu"
        self._is_yolo: bool = False

    def load(self) -> bool:
        """Load weights file onto target device."""
        path = Path(self.model_path)
        if not path.is_file():
            logger.error("Model file does not exist", path=str(path))
            return False

        try:
            import torch

            # Determine compute device
            if self.device == "auto":
                if torch.cuda.is_available():
                    self._resolved_device = "cuda:0"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self._resolved_device = "mps"
                else:
                    self._resolved_device = "cpu"
            else:
                self._resolved_device = self.device

            # Check if this is a YOLO model
            if "yolo" in path.name.lower():
                from ultralytics import YOLO

                self._model = YOLO(str(path))
                self._is_yolo = True
                logger.info(
                    "Loaded YOLO model via Ultralytics",
                    path=path.name,
                    device=self._resolved_device,
                )
            else:
                # Standard PyTorch checkpoint or TorchScript
                try:
                    self._model = torch.jit.load(str(path), map_location=self._resolved_device)
                    self._model.eval()
                except Exception:
                    checkpoint = torch.load(
                        str(path), map_location=self._resolved_device, weights_only=False
                    )
                    if isinstance(checkpoint, dict) and (
                        "fc.weight" in checkpoint or "block1.sgcn.conv.weight" in checkpoint
                    ):
                        # ST-GCN HAR Architecture
                        try:
                            from orion_ai.activity.stgcn.model import STGCNHARModel
                        except ImportError:
                            import sys

                            sys.path.insert(
                                0, str(Path(__file__).resolve().parent.parent.parent / "ai" / "src")
                            )
                            from orion_ai.activity.stgcn.model import STGCNHARModel

                        num_classes = (
                            checkpoint["fc.weight"].shape[0] if "fc.weight" in checkpoint else 8
                        )
                        har_model = STGCNHARModel(in_channels=4, num_classes=num_classes)
                        har_model.load_state_dict(checkpoint)
                        har_model.to(self._resolved_device)
                        har_model.eval()
                        self._model = har_model
                    elif hasattr(checkpoint, "eval"):
                        self._model = checkpoint
                        self._model.to(self._resolved_device)
                        self._model.eval()
                    else:
                        self._model = checkpoint
                self._is_yolo = False
                logger.info(
                    "Loaded PyTorch model checkpoint", path=path.name, device=self._resolved_device
                )

            self._is_loaded = True
            return True
        except Exception as exc:
            logger.error("Failed to load PyTorch model", path=str(path), error=str(exc))
            return False

    def predict(self, input_data: Any) -> Any:
        """Run forward prediction."""
        if not self._is_loaded or self._model is None:
            raise ModelError(f"Model at '{self.model_path}' is not loaded.")

        if self._is_yolo:
            # Ultralytics inference
            return self._model(
                input_data,
                device=self._resolved_device,
                verbose=False,
            )
        # Custom PyTorch model invocation
        import torch

        if isinstance(input_data, torch.Tensor):
            tensor = input_data.to(self._resolved_device)
        else:
            tensor = torch.from_numpy(input_data).to(self._resolved_device)

        with torch.no_grad():
            if callable(self._model):
                return self._model(tensor)
            return self._model

    def unload(self) -> None:
        """Purge model from memory."""
        self._model = None
        self._is_loaded = False
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except Exception:
            pass
        logger.info("Unloaded model from memory", path=self.model_path)
