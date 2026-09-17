"""ModelManager orchestrating multi-model lifecycles, backend dispatch, and benchmarking."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Literal

from app.core.exceptions import ModelNotFoundError
from app.core.logging import get_logger
from app.core.paths import paths
from app.models.inference_backend import InferenceBackend
from app.models.onnx_backend import ONNXBackend
from app.models.pytorch_backend import PyTorchBackend
from app.models.tensorrt_backend import TensorRTBackend

logger = get_logger("app.models.manager")


class ModelManager:
    """Manages discovery, loading, lifecycle, and benchmarking of AI models."""

    def __init__(self) -> None:
        self._models: dict[str, InferenceBackend] = {}
        self._manifests: dict[str, dict[str, Any]] = {}
        self._latencies: dict[str, float] = {}
        self._lock = threading.RLock()

    def get_backend(
        self,
        model_path: str | Path,
        backend_type: Literal["auto", "pytorch", "onnx", "tensorrt"] = "auto",
        device: str = "auto",
    ) -> InferenceBackend:
        """Create an inference backend instance matching the desired framework."""
        path_str = str(model_path)
        resolved_path = paths.resolve_model_path(path_str)

        if not resolved_path.is_file():
            # Check relative to repo
            candidate = paths.root / path_str
            if candidate.is_file():
                resolved_path = candidate
            else:
                raise ModelNotFoundError(f"Model weight file not found: {path_str}")

        resolved_str = str(resolved_path)

        if backend_type == "auto":
            suffix = resolved_path.suffix.lower()
            if suffix == ".engine":
                backend_type = "tensorrt"
            elif suffix == ".onnx":
                backend_type = "onnx"
            else:
                backend_type = "pytorch"

        if backend_type == "tensorrt":
            return TensorRTBackend(resolved_str, device=device)
        if backend_type == "onnx":
            return ONNXBackend(resolved_str, device=device)
        return PyTorchBackend(resolved_str, device=device)

    def load_model(
        self,
        name: str,
        model_path: str | Path,
        backend_type: Literal["auto", "pytorch", "onnx", "tensorrt"] = "auto",
        device: str = "auto",
    ) -> bool:
        """Load and register an AI model."""
        with self._lock:
            if name in self._models:
                self._models[name].unload()

            try:
                backend = self.get_backend(model_path, backend_type, device)
                success = backend.load()
                if success:
                    self._models[name] = backend
                    self._load_manifest(name, model_path)
                    logger.info("Registered and loaded model", name=name, path=str(model_path))
                    return True
                return False
            except Exception as exc:
                logger.error("Failed to load model", name=name, error=str(exc))
                return False

    def get_model(self, name: str) -> InferenceBackend | None:
        """Retrieve an active model backend."""
        with self._lock:
            return self._models.get(name)

    def unload_model(self, name: str) -> None:
        """Unload and unregister a model."""
        with self._lock:
            if name in self._models:
                self._models[name].unload()
                del self._models[name]
                logger.info("Unloaded model", name=name)

    def unload_all(self) -> None:
        """Unload all active models."""
        with self._lock:
            for name in list(self._models.keys()):
                self.unload_model(name)

    def benchmark_model(self, name: str, dummy_input: Any, iterations: int = 10) -> float:
        """Measure average forward inference latency in milliseconds."""
        backend = self.get_model(name)
        if backend is None or not backend.is_loaded:
            return 0.0

        # Warmup
        try:
            backend.predict(dummy_input)
        except Exception:
            return 0.0

        times = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            backend.predict(dummy_input)
            times.append((time.perf_counter() - t0) * 1000.0)

        avg_latency = sum(times) / len(times)
        with self._lock:
            self._latencies[name] = avg_latency
        return avg_latency

    def get_status_overview(self) -> list[dict[str, Any]]:
        """Return operational telemetry for all managed models."""
        with self._lock:
            overview = []
            for name, backend in self._models.items():
                manifest = self._manifests.get(name, {})
                overview.append(
                    {
                        "name": name,
                        "loaded": backend.is_loaded,
                        "backend": type(backend).__name__,
                        "device": backend.device,
                        "path": Path(backend.model_path).name,
                        "version": manifest.get("version", "1.0.0"),
                        "latency_ms": round(self._latencies.get(name, 0.0), 2),
                    }
                )
            return overview

    def _load_manifest(self, name: str, model_path: str | Path) -> None:
        p = Path(model_path)
        manifest_path = p.with_suffix(".manifest.json")
        if not manifest_path.is_file():
            manifest_path = p.parent / f"{p.stem}.manifest.json"
        if not manifest_path.is_file():
            manifest_path = p.parent / "model_manifest.json"

        if manifest_path.is_file():
            try:
                with manifest_path.open("r", encoding="utf-8") as f:
                    self._manifests[name] = json.load(f)
            except Exception:
                pass


# Global model manager singleton
model_manager = ModelManager()
