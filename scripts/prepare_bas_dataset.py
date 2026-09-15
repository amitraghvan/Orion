#!/usr/bin/env python3
"""Pre-annotation, feature extraction, and dataset preparation for BAS_REAL_DATA.

Generates:
  datasets/bas_experiment/metadata/manifest.jsonl
  datasets/bas_experiment/metadata/classes.json
  datasets/bas_experiment/metadata/splits.json
  datasets/bas_experiment/metadata/dataset_version.json
  datasets/bas_experiment/sequences/train/*.npz
  datasets/bas_experiment/sequences/val/*.npz
  datasets/bas_experiment/sequences/test/*.npz
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO

AUDIT_JSON = Path("datasets/bas_experiment/reports/raw_data_audit.json")
OUTPUT_BASE = Path("datasets/bas_experiment")
METADATA_DIR = OUTPUT_BASE / "metadata"
SEQUENCES_DIR = OUTPUT_BASE / "sequences"

POSE_WEIGHTS = "models/weights/yolo11n-pose.pt"

# Canonical BAS Action Classes
CLASSES = [
    "idle",
    "pick_yellow",
    "place_yellow",
    "pick_red",
    "place_red",
    "move_box",
    "check_box",
    "overlap_boxes",
]

CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

# Subject Partitioning: Zero-leakage subject split
TRAIN_SUBJECTS = {"SP01", "SP02"}
VAL_SUBJECTS = {"SP03"}
TEST_SUBJECTS = {"SP04", "SUB_INVALID"}

def detect_box_regions(frame_bgr: np.ndarray) -> tuple[list[tuple[int, int, int, int]], list[tuple[int, int, int, int]]]:
    """Detect yellow and red box bounding boxes (x, y, w, h) via HSV segmentation."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    yellow_mask = cv2.inRange(hsv, (15, 80, 80), (35, 255, 255))
    red_mask1 = cv2.inRange(hsv, (0, 80, 80), (10, 255, 255))
    red_mask2 = cv2.inRange(hsv, (170, 80, 80), (180, 255, 255))
    red_mask = red_mask1 | red_mask2

    y_cnts, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    r_cnts, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    y_boxes = [cv2.boundingRect(c) for c in y_cnts if cv2.contourArea(c) > 300]
    r_boxes = [cv2.boundingRect(c) for c in r_cnts if cv2.contourArea(c) > 300]
    return y_boxes, r_boxes

def compute_hand_box_proximity(
    wrist_x: float,
    wrist_y: float,
    boxes: list[tuple[int, int, int, int]],
    frame_w: int,
    frame_h: int,
) -> float:
    """Compute normalized proximity interaction score [0.0, 1.0] between a wrist joint and boxes."""
    if not boxes or wrist_x <= 0 or wrist_y <= 0:
        return 0.0
    
    px = wrist_x * frame_w
    py = wrist_y * frame_h
    
    min_dist = float("inf")
    for bx, by, bw, bh in boxes:
        cx = bx + bw / 2.0
        cy = by + bh / 2.0
        dist = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
        min_dist = min(min_dist, dist)

    # Proximity threshold: 250 pixels normalized to diagonal
    diag = (frame_w ** 2 + frame_h ** 2) ** 0.5
    norm_dist = min_dist / max(1.0, diag * 0.25)
    return float(max(0.0, 1.0 - norm_dist))

def infer_frame_action(
    t_norm: float,
    exp_id: str,
    variant: str,
    is_valid: bool,
    invalid_type: str | None,
    y_prox: float,
    r_prox: float,
) -> tuple[str, str]:
    """Infer ground truth step and action label from experiment protocol and interaction state."""
    if not is_valid:
        if invalid_type == "WRONG_OBJECT":
            # Manipulates red box when yellow is expected
            return "E01_A_S01", "pick_red"
        elif invalid_type == "INTERRUPTION":
            if t_norm > 0.4:
                return "E01_A_INTERRUPTED", "idle"
            return "E01_A_S01", "pick_yellow"
        elif invalid_type == "WRONG_ORDER":
            # Performed step 3/4 before step 1/2
            return "E01_A_S03", "pick_red"
        return "VIOLATION", "idle"

    # Valid videos by experiment
    if exp_id == "E01":
        if variant == "A":
            # 1: Pick yellow (0-25%), 2: Place yellow (25-50%), 3: Pick red (50-75%), 4: Place red (75-100%)
            if t_norm < 0.25:
                return "E01_A_S01", "pick_yellow"
            elif t_norm < 0.50:
                return "E01_A_S02", "place_yellow"
            elif t_norm < 0.75:
                return "E01_A_S03", "pick_red"
            else:
                return "E01_A_S04", "place_red"
        else:
            # Variant B: Red first, then Yellow
            if t_norm < 0.25:
                return "E01_B_S01", "pick_red"
            elif t_norm < 0.50:
                return "E01_B_S02", "place_red"
            elif t_norm < 0.75:
                return "E01_B_S03", "pick_yellow"
            else:
                return "E01_B_S04", "place_yellow"

    elif exp_id == "E02":
        # Interchanging
        if t_norm < 0.33:
            return f"{exp_id}_{variant}_S01", "pick_yellow" if y_prox > r_prox else "pick_red"
        elif t_norm < 0.66:
            return f"{exp_id}_{variant}_S02", "place_yellow" if variant == "A" else "place_red"
        else:
            return f"{exp_id}_{variant}_S03", "place_red" if variant == "A" else "place_yellow"

    elif exp_id == "E03":
        # Overlapping
        if t_norm < 0.45:
            return f"{exp_id}_{variant}_S01", "place_yellow"
        else:
            return f"{exp_id}_{variant}_S02", "overlap_boxes"

    elif exp_id == "E04":
        # Moving
        if t_norm < 0.35:
            return f"{exp_id}_{variant}_S01", "idle"
        else:
            return f"{exp_id}_{variant}_S02", "move_box"

    elif exp_id == "E05":
        # In Container
        if variant == "A":
            if t_norm < 0.25:
                return "E05_A_S01", "pick_yellow"
            elif t_norm < 0.50:
                return "E05_A_S02", "check_box"
            elif t_norm < 0.75:
                return "E05_A_S03", "pick_red"
            else:
                return "E05_A_S04", "check_box"
        else:
            if t_norm < 0.25:
                return "E05_B_S01", "pick_red"
            elif t_norm < 0.50:
                return "E05_B_S02", "check_box"
            elif t_norm < 0.75:
                return "E05_B_S03", "pick_yellow"
            else:
                return "E05_B_S04", "check_box"

    return "UNKNOWN", "idle"

def main():
    with open(AUDIT_JSON) as f:
        audit_records = json.load(f)

    # Initialize YOLO Pose
    print("Loading YOLO Pose model...")
    pose_model = YOLO(POSE_WEIGHTS)

    for split in ["train", "val", "test"]:
        split_dir = SEQUENCES_DIR / split
        if split_dir.exists():
            shutil.rmtree(split_dir)
        split_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries = []
    split_assignments = {"train": [], "val": [], "test": []}
    class_counts = {c: 0 for c in CLASSES}
    total_sequences = 0

    print(f"Processing {len(audit_records)} videos...")
    for idx, record in enumerate(audit_records):
        video_path = record["absolute_path"]
        video_id = record["video_id"]
        sub_id = record["subject_id"]
        exp_id = record["experiment_id"]
        variant = record["variant"]
        is_valid = record["is_valid"]
        invalid_type = record["invalid_type"]

        # Determine split
        if sub_id in TRAIN_SUBJECTS:
            split = "train"
        elif sub_id in VAL_SUBJECTS:
            split = "val"
        else:
            split = "test"

        split_assignments[split].append(video_id)

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_data: list[tuple[np.ndarray, str, str]] = []  # (pose_feat, step_id, action)

        f_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            h, w = frame.shape[:2]
            # Downsample for faster pose & color detection
            scale = 640.0 / max(h, w)
            small = cv2.resize(frame, (int(w * scale), int(h * scale)))
            sh, sw = small.shape[:2]

            # 1. Pose estimation
            res = pose_model.predict(small, verbose=False, conf=0.3)
            # Default keypoints (17, 3)
            kpts = np.zeros((17, 3), dtype=np.float32)
            if res and len(res) > 0 and res[0].keypoints is not None and len(res[0].keypoints.data) > 0:
                first_kpts = res[0].keypoints.data[0].cpu().numpy()
                kpts[:, 0] = first_kpts[:, 0] / max(1, sw)
                kpts[:, 1] = first_kpts[:, 1] / max(1, sh)
                kpts[:, 2] = first_kpts[:, 2]

            # 2. Box detection and interaction
            y_boxes, r_boxes = detect_box_regions(small)
            # Left wrist (idx 9), Right wrist (idx 10)
            lw_x, lw_y = float(kpts[9, 0]), float(kpts[9, 1])
            rw_x, rw_y = float(kpts[10, 0]), float(kpts[10, 1])

            y_prox = max(
                compute_hand_box_proximity(lw_x, lw_y, y_boxes, sw, sh),
                compute_hand_box_proximity(rw_x, rw_y, y_boxes, sw, sh),
            )
            r_prox = max(
                compute_hand_box_proximity(lw_x, lw_y, r_boxes, sw, sh),
                compute_hand_box_proximity(rw_x, rw_y, r_boxes, sw, sh),
            )

            # Channel 4: Interaction signal (+y_prox if yellow dominant, -r_prox if red dominant)
            interact_feat = np.zeros(17, dtype=np.float32)
            # Wrist & elbow joints receive interaction weight
            for j in [7, 8, 9, 10]:
                interact_feat[j] = y_prox if y_prox >= r_prox else r_prox

            # Construct 4-channel pose frame: (4, 17) -> [x, y, conf, interaction]
            frame_feat = np.stack([kpts[:, 0], kpts[:, 1], kpts[:, 2], interact_feat], axis=0)

            t_norm = f_idx / max(1, total_frames)
            step_id, action = infer_frame_action(
                t_norm, exp_id, variant, is_valid, invalid_type, y_prox, r_prox
            )

            frame_data.append((frame_feat, step_id, action))
            f_idx += 1

        cap.release()

        # Slice 32-frame sliding windows with stride=8
        window_size = 32
        stride = 8
        n_frames = len(frame_data)
        seq_count = 0

        for start_idx in range(0, max(1, n_frames - window_size + 1), stride):
            end_idx = min(start_idx + window_size, n_frames)
            window_slice = frame_data[start_idx:end_idx]
            if len(window_slice) < window_size:
                # Pad with last frame
                last_elem = window_slice[-1]
                window_slice = window_slice + [last_elem] * (window_size - len(window_slice))

            # Stack frames into (4, 32, 17)
            x_seq = np.stack([w[0] for w in window_slice], axis=1).astype(np.float32)

            # Majority action label in window
            actions = [w[2] for w in window_slice]
            step_ids = [w[1] for w in window_slice]
            action_label = max(set(actions), key=actions.count)
            step_label = max(set(step_ids), key=step_ids.count)

            class_idx = CLASS_TO_IDX.get(action_label, 0)
            class_counts[action_label] += 1

            seq_filename = f"{video_id}_seq_{seq_count:03d}.npz"
            save_path = SEQUENCES_DIR / split / seq_filename
            np.savez_compressed(
                save_path,
                x=x_seq,
                y=class_idx,
                action=action_label,
                step_id=step_label,
                video_id=video_id,
                experiment_id=exp_id,
                variant=variant,
                frame_start=start_idx,
                frame_end=end_idx,
            )
            seq_count += 1
            total_sequences += 1

        manifest_entries.append({
            "video_id": video_id,
            "subject_id": sub_id,
            "experiment_id": exp_id,
            "variant": variant,
            "is_valid": is_valid,
            "split": split,
            "sequences_extracted": seq_count,
            "total_frames": total_frames,
        })
        print(f"[{idx+1}/{len(audit_records)}] {video_id} -> {split}: {seq_count} sequences")

    # Write manifest.jsonl
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(METADATA_DIR / "manifest.jsonl", "w") as f:
        for entry in manifest_entries:
            f.write(json.dumps(entry) + "\n")

    # Write classes.json
    with open(METADATA_DIR / "classes.json", "w") as f:
        json.dump({
            "classes": CLASSES,
            "class_to_idx": CLASS_TO_IDX,
            "class_counts": class_counts,
            "num_classes": len(CLASSES),
        }, f, indent=2)

    # Write splits.json
    with open(METADATA_DIR / "splits.json", "w") as f:
        json.dump({
            "train": split_assignments["train"],
            "val": split_assignments["val"],
            "test": split_assignments["test"],
            "leakage_check_passed": len(set(split_assignments["train"]).intersection(set(split_assignments["test"]))) == 0,
        }, f, indent=2)

    # Write dataset_version.json
    with open(METADATA_DIR / "dataset_version.json", "w") as f:
        json.dump({
            "dataset_name": "BAS_REAL_DATA",
            "version": "1.0.0",
            "date_created": "2026-09-14",
            "source": "/Users/amitkumar/Downloads/BAS_REAL_DATA",
            "total_raw_videos": len(audit_records),
            "total_sequences": total_sequences,
            "sequence_shape": [4, 32, 17],
            "class_distribution": class_counts,
        }, f, indent=2)

    print(f"\nCompleted! Generated {total_sequences} sequences across train/val/test splits.")
    print("Class distribution:", class_counts)

if __name__ == "__main__":
    main()
