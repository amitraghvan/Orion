"""ONNX Runtime inference backend supporting CPU and GPU execution providers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.exceptions import ModelError
from app.core.logging import get_logger
from app.models.inference_backend import InferenceBackend

logger = get_logger("app.models.onnx")


class ONNXBackend(InferenceBackend):
    """Executes exported ONNX models via onnxruntime."""

    def __init__(self, model_path: str, device: str = "auto") -> None:
        super().__init__(model_path, device)
        self._session: Any = None
        self._input_names: list[str] = []
        self._output_names: list[str] = []

    def load(self) -> bool:
        path = Path(self.model_path)
        if not path.is_file():
            logger.error("ONNX model file does not exist", path=str(path))
            return False

        try:
            import onnxruntime as ort

            available_providers = ort.get_available_providers()
            providers = []
            if self.device in ("auto", "cuda") and "CUDAExecutionProvider" in available_providers:
                providers.append("CUDAExecutionProvider")
            if "CoreMLExecutionProvider" in available_providers:
                providers.append("CoreMLExecutionProvider")
            providers.append("CPUExecutionProvider")

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            self._session = ort.InferenceSession(str(path), sess_options=opts, providers=providers)
            self._input_names = [i.name for i in self._session.get_inputs()]
            self._output_names = [o.name for o in self._session.get_outputs()]

            self._is_loaded = True
            logger.info("ONNX session created", path=path.name, providers=self._session.get_providers())
            return True
        except Exception as exc:
            logger.error("Failed to load ONNX model", path=str(path), error=str(exc))
            return False

    def predict(self, input_data: Any) -> Any:
        if not self._is_loaded or self._session is None:
            raise ModelError(f"ONNX model at '{self.model_path}' is not loaded.")

        feed_dict = {}
        if isinstance(input_data, dict):
            feed_dict = input_data
        elif isinstance(input_data, (list, tuple)):
            for name, val in zip(self._input_names, input_data):
                feed_dict[name] = val
        else:
            if self._input_names:
                feed_dict[self._input_names[0]] = input_data

        return self._session.run(self._output_names, feed_dict)

    def unload(self) -> None:
        self._session = None
        self._is_loaded = False
        logger.info("Unloaded ONNX model", path=self.model_path)
