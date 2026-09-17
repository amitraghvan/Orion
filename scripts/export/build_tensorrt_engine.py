"""NVIDIA TensorRT engine serialization pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_engine_from_onnx(
    onnx_path: str, engine_path: str | None = None, fp16: bool = True
) -> bool:
    src = Path(onnx_path)
    if not src.is_file():
        print(f"❌ Source ONNX model not found: {src}")
        return False

    dst = Path(engine_path) if engine_path else src.with_suffix(".engine")
    dst.parent.mkdir(parents=True, exist_ok=True)

    print(f"Building TensorRT serialized engine from '{src}' -> '{dst}' (FP16={fp16})...")

    try:
        import tensorrt as trt

        logger = trt.Logger(trt.Logger.INFO)
        builder = trt.Builder(logger)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, logger)

        with src.open("rb") as f:
            if not parser.parse(f.read()):
                for error in range(parser.num_errors):
                    print("TensorRT ONNX Parser error:", parser.get_error(error))
                return False

        config = builder.create_builder_config()
        if fp16 and builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)

        serialized_engine = builder.build_serialized_network(network, config)
        if serialized_engine is None:
            print("❌ Failed to build TensorRT engine.")
            return False

        with dst.open("wb") as f:
            f.write(serialized_engine)

        print(f"✓ TensorRT engine successfully saved to: {dst}")
        return True
    except (ImportError, Exception) as exc:
        print(
            f"⚠️ TensorRT build skipped: {exc} (Graceful fallback to ONNX/PyTorch will be used at runtime)."
        )
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION TensorRT Engine Builder")
    parser.add_argument("--onnx", required=True, help="Path to source .onnx model")
    parser.add_argument("--engine", default=None, help="Target .engine destination path")
    args = parser.parse_args()

    build_engine_from_onnx(args.onnx, args.engine)


if __name__ == "__main__":
    main()
