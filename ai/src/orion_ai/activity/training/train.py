"""Training script for ST-GCN Temporal Human Activity Recognition model."""

import argparse
import logging
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.utils.data import DataLoader

from orion_ai.activity.stgcn.model import STGCNHARModel
from orion_ai.activity.training.dataset import build_synthetic_dataset

logger = logging.getLogger(__name__)


def train_stgcn_model(
    save_path: str = "models/weights/stgcn_har_v1.pt",
    epochs: int = 15,
    batch_size: int = 32,
    lr: float = 1e-3,
    samples_per_class: int = 120,
    seed: int = 42,
    device: str = "cpu",
) -> dict[str, Any]:
    """Train ST-GCN model on skeleton action sequences and export weights."""
    torch.manual_seed(seed)

    train_ds, val_ds = build_synthetic_dataset(
        samples_per_class=samples_per_class,
        num_frames=32,
        base_seed=seed,
    )

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    dev = torch.device(device)
    model = STGCNHARModel(
        in_channels=4,
        num_classes=6,
        dropout=0.2,
    ).to(dev)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    best_val_acc = 0.0
    metrics_history: list[dict[str, float]] = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        correct_train = 0
        total_train = 0

        for feats, labels in train_loader:
            b_feats = feats.to(dev)
            b_labels = labels.to(dev)

            optimizer.zero_grad()
            logits = model(b_feats)
            loss = criterion(logits, b_labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * len(b_labels)
            preds = logits.argmax(dim=1)
            correct_train += (preds == b_labels).sum().item()
            total_train += len(b_labels)

        train_loss = total_loss / max(total_train, 1)
        train_acc = correct_train / max(total_train, 1)

        # Validation
        model.eval()
        val_loss = 0.0
        correct_val = 0
        total_val = 0

        with torch.no_grad():
            for feats, labels in val_loader:
                b_feats = feats.to(dev)
                b_labels = labels.to(dev)
                logits = model(b_feats)
                loss = criterion(logits, b_labels)
                val_loss += loss.item() * len(b_labels)
                preds = logits.argmax(dim=1)
                correct_val += (preds == b_labels).sum().item()
                total_val += len(b_labels)

        val_loss_avg = val_loss / max(total_val, 1)
        val_acc = correct_val / max(total_val, 1)

        metrics_history.append({
            "epoch": float(epoch),
            "train_loss": train_loss,
            "train_acc": train_acc,
            "val_loss": val_loss_avg,
            "val_acc": val_acc,
        })

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            out_path = Path(save_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), out_path)

    return {
        "epochs": epochs,
        "best_val_acc": best_val_acc,
        "final_train_loss": train_loss,
        "final_val_loss": val_loss_avg,
        "save_path": save_path,
        "history": metrics_history,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ST-GCN for BAS HAR.")
    parser.add_argument("--save-path", default="models/weights/stgcn_har_v1.pt")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--samples-per-class", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger.info("Starting ST-GCN training with synthetic kinematic dataset...")
    results = train_stgcn_model(
        save_path=args.save_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        samples_per_class=args.samples_per_class,
        seed=args.seed,
    )
    logger.info("Training complete: best_val_acc=%.4f saved to %s", results["best_val_acc"], results["save_path"])


if __name__ == "__main__":
    main()
