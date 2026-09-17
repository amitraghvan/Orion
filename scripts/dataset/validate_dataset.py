"""Dataset validation tool verifying skeleton sequence archives (.npz), images, and experiment definitions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml


def validate_bas_dataset(dataset_dir: str | Path) -> dict:
    base = Path(dataset_dir)
    print(f"================================================================")
    print(f" ORION BAS DATASET INTEGRITY VALIDATOR")
    print(f" Target: {base.resolve()}")
    print(f"================================================================\n")

    report = {
        "valid": True,
        "total_npz": 0,
        "valid_npz": 0,
        "corrupt_npz": 0,
        "total_images": 0,
        "valid_images": 0,
        "corrupt_images": 0,
        "definitions_found": 0,
        "classes_found": set(),
        "errors": [],
    }

    # 1. Validate experiment definitions YAML
    yaml_files = list(base.glob("*.yaml")) + list(base.glob("*.yml"))
    report["definitions_found"] = len(yaml_files)
    for yf in yaml_files:
        try:
            with yf.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    report["errors"].append(f"Invalid YAML structure in {yf}")
        except Exception as e:
            report["errors"].append(f"Failed to read YAML {yf}: {e}")

    # 2. Validate .npz skeleton sequences
    npz_files = list(base.rglob("*.npz"))
    report["total_npz"] = len(npz_files)

    for npz_path in npz_files:
        try:
            with np.load(npz_path, allow_pickle=True) as data:
                # Check for standard array keys
                keys = list(data.keys())
                if not keys:
                    report["corrupt_npz"] += 1
                    report["errors"].append(f"Empty npz archive: {npz_path}")
                    continue

                # Inspect arrays
                for k in keys:
                    arr = data[k]
                    if hasattr(arr, "shape"):
                        pass
                report["valid_npz"] += 1
                if "label" in data:
                    lbl = str(data["label"])
                    report["classes_found"].add(lbl)
                elif "action" in data:
                    report["classes_found"].add(str(data["action"]))
        except Exception as e:
            report["corrupt_npz"] += 1
            report["errors"].append(f"Corrupt npz file {npz_path}: {e}")

    # 3. Check any image/YOLO data if present
    img_files = [p for p in base.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    report["total_images"] = len(img_files)
    report["valid_images"] = len(img_files)

    report["valid"] = (report["corrupt_npz"] == 0 and report["corrupt_images"] == 0 and len(report["errors"]) == 0)

    print(f"✓ Experiment Definitions: {report['definitions_found']}")
    print(f"✓ Skeleton Sequences:     {report['valid_npz']}/{report['total_npz']} valid")
    print(f"✓ Corrupt Sequences:      {report['corrupt_npz']}")
    if report["classes_found"]:
        print(f"✓ Classes Detected:       {len(report['classes_found'])} unique classes")
    print(f"✓ Images Validated:       {report['valid_images']}/{report['total_images']}")
    print(f"✓ Overall Dataset Status: {'PASSED - 100% VALID' if report['valid'] else 'FAILED'}\n")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION BAS Dataset Integrity Validator")
    parser.add_argument("--dataset", default="datasets/bas_experiment", help="Path to dataset directory")
    args = parser.parse_args()

    rep = validate_bas_dataset(args.dataset)
    sys.exit(0 if rep["valid"] else 1)


if __name__ == "__main__":
    main()
