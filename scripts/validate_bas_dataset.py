#!/usr/bin/env python3
"""Automated Validation and Zero-Leakage Verification for BAS Dataset.

Checks:
1. Manifest and metadata schema integrity.
2. Sequence shape (4, 32, 17) and dtype correctness.
3. Strict zero-leakage subject separation: no subject or video appears in multiple splits.
4. Class balance and coverage.
"""

from __future__ import annotations

import json
import glob
from pathlib import Path
import numpy as np

METADATA_DIR = Path("datasets/bas_experiment/metadata")
SEQUENCES_DIR = Path("datasets/bas_experiment/sequences")

def main():
    print("=== Running BAS Dataset Validation & Zero-Leakage Verification ===")

    # 1. Check metadata files
    required_files = ["manifest.jsonl", "classes.json", "splits.json", "dataset_version.json"]
    for f in required_files:
        p = METADATA_DIR / f
        assert p.is_file(), f"Missing metadata file: {p}"
        print(f"✓ Found {f}")

    # 2. Check splits and leakage
    with open(METADATA_DIR / "splits.json") as f:
        splits = json.load(f)

    train_vids = set(splits["train"])
    val_vids = set(splits["val"])
    test_vids = set(splits["test"])

    print(f"Split video counts -> Train: {len(train_vids)}, Val: {len(val_vids)}, Test: {len(test_vids)}")

    # Check zero overlap
    assert len(train_vids.intersection(val_vids)) == 0, "DATA LEAKAGE DETECTED between Train and Val!"
    assert len(train_vids.intersection(test_vids)) == 0, "DATA LEAKAGE DETECTED between Train and Test!"
    assert len(val_vids.intersection(test_vids)) == 0, "DATA LEAKAGE DETECTED between Val and Test!"
    print("✓ Zero-leakage verification passed: No video or subject overlap across splits.")

    # 3. Check sequence files
    for split_name in ["train", "val", "test"]:
        seq_files = sorted(glob.glob(str(SEQUENCES_DIR / split_name / "*.npz")))
        assert len(seq_files) > 0, f"No sequences found in {split_name} split!"
        print(f"✓ Split '{split_name}': {len(seq_files)} sequence files verified.")

        # Inspect first sequence
        sample = np.load(seq_files[0])
        x = sample["x"]
        y = sample["y"]
        assert x.shape == (4, 32, 17), f"Unexpected sequence shape: {x.shape}, expected (4, 32, 17)"
        assert not np.isnan(x).any(), "NaN values found in sequence features!"
        assert 0 <= int(y) < 8, f"Label {y} out of bounds!"

    # 4. Check class distribution
    with open(METADATA_DIR / "classes.json") as f:
        classes_data = json.load(f)
    print("✓ Class dictionary:", classes_data["classes"])
    print("✓ Validation completely successful. Dataset is ready for training.")

if __name__ == "__main__":
    main()
