#!/usr/bin/env python3
"""Train / fine-tune ST-GCN temporal action recognition model on real BAS_REAL_DATA sequences.

Produces:
  models/bas_experiment/best.pt
  models/bas_experiment/last.pt
  models/bas_experiment/metrics.json
  models/bas_experiment/model_manifest.json
"""

from __future__ import annotations

import glob
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from orion_ai.activity.stgcn.model import STGCNHARModel

SEQUENCES_DIR = Path("datasets/bas_experiment/sequences")
MODELS_DIR = Path("models/bas_experiment")
CHECKPOINTS_DIR = MODELS_DIR / "checkpoints"
PRETRAINED_WEIGHTS = Path("models/weights/stgcn_har_v1.pt")

NUM_CLASSES = 8
EPOCHS = 25
BATCH_SIZE = 16
LEARNING_RATE = 1e-3

class BASSequenceDataset(Dataset):
    def __init__(self, npz_files: list[str]) -> None:
        self.files = npz_files
        self.data: list[tuple[np.ndarray, int]] = []
        for f in self.files:
            item = np.load(f)
            x = item["x"].astype(np.float32)
            y = int(item["y"])
            self.data.append((x, y))

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x, y = self.data[idx]
        return torch.from_numpy(x), torch.tensor(y, dtype=torch.long)

def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    print("=== Training ORION ST-GCN on BAS_REAL_DATA ===")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"))
    print(f"Execution Device: {device}")

    train_files = sorted(glob.glob(str(SEQUENCES_DIR / "train" / "*.npz")))
    val_files = sorted(glob.glob(str(SEQUENCES_DIR / "val" / "*.npz")))

    print(f"Loaded {len(train_files)} training samples, {len(val_files)} validation samples.")
    assert len(train_files) > 0, "No training samples found!"
    assert len(val_files) > 0, "No validation samples found!"

    train_ds = BASSequenceDataset(train_files)
    val_ds = BASSequenceDataset(val_files)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    # Initialize model
    model = STGCNHARModel(in_channels=4, num_classes=NUM_CLASSES, dropout=0.2)

    # Transfer learning: load pretrained feature backbone if compatible
    if PRETRAINED_WEIGHTS.is_file():
        try:
            print(f"Loading pretrained backbone from {PRETRAINED_WEIGHTS}...")
            state_dict = torch.load(PRETRAINED_WEIGHTS, map_location="cpu")
            # Filter out final classifier weights due to class dimension change (6 -> 8)
            filtered_dict = {
                k: v for k, v in state_dict.items()
                if not k.startswith("fcn") and k in model.state_dict() and v.shape == model.state_dict()[k].shape
            }
            model.load_state_dict(filtered_dict, strict=False)
            print(f"Successfully transferred {len(filtered_dict)} backbone layers.")
        except Exception as exc:
            print(f"Warning: Pretrained weight transfer skipped ({exc}). Training from scratch.")

    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-5)

    best_val_acc = 0.0
    history = []

    t_start = time.time()

    for epoch in range(1, EPOCHS + 1):
        # Training loop
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for x_b, y_b in train_loader:
            x_b = x_b.to(device)
            y_b = y_b.to(device)

            optimizer.zero_grad()
            logits = model(x_b)
            loss = criterion(logits, y_b)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(y_b)
            preds = logits.argmax(dim=1)
            train_correct += (preds == y_b).sum().item()
            train_total += len(y_b)

        scheduler.step()

        train_loss /= max(1, train_total)
        train_acc = train_correct / max(1, train_total)

        # Validation loop
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for x_v, y_v in val_loader:
                x_v = x_v.to(device)
                y_v = y_v.to(device)
                logits_v = model(x_v)
                loss_v = criterion(logits_v, y_v)
                val_loss += loss_v.item() * len(y_v)
                preds_v = logits_v.argmax(dim=1)
                val_correct += (preds_v == y_v).sum().item()
                val_total += len(y_v)

        val_loss /= max(1, val_total)
        val_acc = val_correct / max(1, val_total)

        epoch_stats = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 4),
            "lr": round(optimizer.param_groups[0]["lr"], 6),
        }
        history.append(epoch_stats)
        print(f"Epoch [{epoch:02d}/{EPOCHS:02d}] Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")

        # Checkpoint save
        ckpt_path = CHECKPOINTS_DIR / f"epoch_{epoch:02d}.pt"
        torch.save(model.state_dict(), ckpt_path)

        # Best model tracking
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_path = MODELS_DIR / "best.pt"
            torch.save(model.state_dict(), best_path)

    # Save last model
    last_path = MODELS_DIR / "last.pt"
    torch.save(model.state_dict(), last_path)

    total_time = round(time.time() - t_start, 2)
    best_digest = compute_sha256(MODELS_DIR / "best.pt")

    metrics_payload = {
        "model_id": "BAS-HAR-v1.0",
        "dataset_name": "BAS_REAL_DATA",
        "dataset_version": "1.0.0",
        "architecture": "stgcn_coco17_interaction",
        "in_channels": 4,
        "num_classes": NUM_CLASSES,
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "training_time_seconds": total_time,
        "best_val_accuracy": round(best_val_acc, 4),
        "history": history,
        "best_model_sha256": best_digest,
    }

    with open(MODELS_DIR / "metrics.json", "w") as f:
        json.dump(metrics_payload, f, indent=2)

    # Save manifest
    manifest_payload = {
        "model_id": "BAS-HAR-v1.0",
        "version": "1.0.0",
        "task": "temporal_action_recognition",
        "architecture": "stgcn_coco17",
        "framework": "pytorch",
        "format": "pt",
        "input_shape": [1, 4, 32, 17],
        "output_schema": "class_logits_8",
        "classes": [
            "idle",
            "pick_yellow",
            "place_yellow",
            "pick_red",
            "place_red",
            "move_box",
            "check_box",
            "overlap_boxes",
        ],
        "sha256": best_digest,
        "creation_timestamp": datetime.now(UTC).isoformat(),
        "notes": "Fine-tuned ST-GCN model on BAS_REAL_DATA spaceflight experiments.",
    }

    with open(MODELS_DIR / "model_manifest.json", "w") as f:
        json.dump(manifest_payload, f, indent=2)

    print(f"\nTraining Complete in {total_time}s! Best Val Accuracy: {best_val_acc * 100:.2f}%")
    print(f"Artifacts saved to: {MODELS_DIR}")

if __name__ == "__main__":
    main()
