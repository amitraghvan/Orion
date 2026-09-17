"""ONNX model export tool for YOLO and ST-GCN models."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch


def export_model_to_onnx(model_path: str, output_path: str | None = None) -> Path:
    src = Path(model_path)
    if not src.is_file():
        raise FileNotFoundError(f"Model weights file not found: {src}")

    dst = Path(output_path) if output_path else src.with_suffix(".onnx")
    dst.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exporting '{src.name}' to ONNX at '{dst}'...")

    if "yolo" in src.name.lower():
        from ultralytics import YOLO
        model = YOLO(str(src))
        exported_path = model.export(format="onnx", imgsz=640, dynamic=True)
        print(f"✓ Ultralytics exported ONNX to: {exported_path}")
        return Path(exported_path)
    else:
        # Standard PyTorch model (e.g. ST-GCN)
        # Input shape for ST-GCN: (1, 4, 32, 17)
        dummy_input = torch.randn(1, 4, 32, 17, dtype=torch.float32)
        model = torch.load(str(src), map_location="cpu", weights_only=False)
        model.eval()

        torch.onnx.export(
            model,
            dummy_input,
            str(dst),
            input_names=["keypoint_sequence"],
            output_names=["activity_logits"],
            dynamic_axes={"keypoint_sequence": {0: "batch_size"}, "activity_logits": {0: "batch_size"}},
            opset_version=17,
        )
        print(f"✓ PyTorch model exported to ONNX: {dst}")
        return dst


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION Model ONNX Exporter")
    parser.add_argument("--model", default="models/weights/yolo11n.pt", help="Path to .pt weights file")
    parser.add_argument("--output", default=None, help="Target .onnx destination path")
    args = parser.parse_args()

    export_model_to_onnx(args.model, args.output)


if __name__ == "__main__":
    main()
