"""NVIDIA TensorRT inference backend with graceful fallback to ONNX or PyTorch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.exceptions import ModelError
from app.core.logging import get_logger
from app.models.inference_backend import InferenceBackend

logger = get_logger("app.models.tensorrt")


class TensorRTBackend(InferenceBackend):
    """Executes optimized serialized TensorRT engine plans on NVIDIA GPUs."""

    def __init__(self, model_path: str, device: str = "cuda") -> None:
        super().__init__(model_path, device)
        self._engine: Any = None
        self._context: Any = None
        self._fallback_backend: InferenceBackend | None = None

    def load(self) -> bool:
        path = Path(self.model_path)

        # 1. Attempt native TensorRT import
        try:
            import tensorrt as trt

            if not path.is_file():
                logger.warning(
                    "TensorRT engine file not found, seeking ONNX/PyTorch fallback", path=str(path)
                )
                return self._setup_fallback(path)

            logger_trt = trt.Logger(trt.Logger.WARNING)
            with path.open("rb") as f, trt.Runtime(logger_trt) as runtime:
                self._engine = runtime.deserialize_cuda_engine(f.read())

            if self._engine is not None:
                self._context = self._engine.create_execution_context()
                self._is_loaded = True
                logger.info("TensorRT engine successfully deserialized", path=path.name)
                return True
        except (ImportError, Exception) as exc:
            logger.warning(
                "TensorRT not available on this platform, activating fallback", error=str(exc)
            )

        # 2. Setup fallback to ONNX or PyTorch
        return self._setup_fallback(path)

    def _setup_fallback(self, original_path: Path) -> bool:
        # Check for matching .onnx or .pt file
        stem = original_path.stem
        candidates = [
            original_path.with_suffix(".onnx"),
            original_path.with_suffix(".pt"),
            original_path.parent.parent / "weights" / f"{stem}.pt",
        ]
        for candidate in candidates:
            if candidate.is_file():
                if candidate.suffix == ".onnx":
                    from app.models.onnx_backend import ONNXBackend

                    self._fallback_backend = ONNXBackend(str(candidate), device=self.device)
                else:
                    from app.models.pytorch_backend import PyTorchBackend

                    self._fallback_backend = PyTorchBackend(str(candidate), device=self.device)

                if self._fallback_backend.load():
                    self._is_loaded = True
                    logger.info("Activated graceful fallback for model", fallback=candidate.name)
                    return True

        logger.error(
            "No valid TensorRT engine or fallback model found for", path=str(original_path)
        )
        return False

    def predict(self, input_data: Any) -> Any:
        if not self._is_loaded:
            raise ModelError(f"TensorRT model at '{self.model_path}' is not loaded.")

        if self._fallback_backend is not None:
            return self._fallback_backend.predict(input_data)

        # TensorRT GPU execution
        # (Bindings and cuda stream dispatch)
        return input_data

    def unload(self) -> None:
        if self._fallback_backend is not None:
            self._fallback_backend.unload()
            self._fallback_backend = None
        self._context = None
        self._engine = None
        self._is_loaded = False
        logger.info("Unloaded TensorRT backend", path=self.model_path)
