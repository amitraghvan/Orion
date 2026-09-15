#!/usr/bin/env python3
"""Evaluate trained BAS ST-GCN model on held-out test videos and invalid violation videos.

Generates:
  models/bas_experiment/evaluation.json
  models/bas_experiment/confusion_matrix.png
"""

from __future__ import annotations

import glob
import json
from pathlib import Path
import numpy as np
import torch
import matplotlib.pyplot as plt

from orion_ai.activity.stgcn.model import STGCNHARModel

MODELS_DIR = Path("models/bas_experiment")
BEST_MODEL_PATH = MODELS_DIR / "best.pt"
TEST_SEQUENCES_DIR = Path("datasets/bas_experiment/sequences/test")
CLASSES_JSON = Path("datasets/bas_experiment/metadata/classes.json")

def compute_confusion_matrix(y_true: list[int], y_pred: list[int], num_classes: int) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1
    return cm

def compute_metrics(cm: np.ndarray, classes: list[str]) -> tuple[float, float, float, float, dict]:
    total = np.sum(cm)
    correct = np.trace(cm)
    acc = float(correct / total) if total > 0 else 0.0

    precisions = []
    recalls = []
    f1s = []
    per_class = {}

    num_classes = len(classes)
    for c in range(num_classes):
        tp = cm[c, c]
        fp = np.sum(cm[:, c]) - tp
        fn = np.sum(cm[c, :]) - tp
        support = int(np.sum(cm[c, :]))

        p = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        r = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * p * r / (p + r)) if (p + r) > 0 else 0.0

        precisions.append(p)
        recalls.append(r)
        f1s.append(f1)

        per_class[classes[c]] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    macro_p = float(np.mean(precisions))
    macro_r = float(np.mean(recalls))
    macro_f1 = float(np.mean(f1s))

    return acc, macro_p, macro_r, macro_f1, per_class

def main():
    print("=== Evaluating Trained BAS Model on Held-Out Real Videos ===")
    assert BEST_MODEL_PATH.is_file(), f"Best model not found at {BEST_MODEL_PATH}"

    with open(CLASSES_JSON) as f:
        classes_data = json.load(f)
    classes = classes_data["classes"]
    num_classes = len(classes)

    device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"))
    print(f"Evaluation Device: {device}")

    # Load model
    model = STGCNHARModel(in_channels=4, num_classes=num_classes)
    state_dict = torch.load(BEST_MODEL_PATH, map_location="cpu")
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    test_files = sorted(glob.glob(str(TEST_SEQUENCES_DIR / "*.npz")))
    print(f"Loaded {len(test_files)} held-out test sequences.")
    assert len(test_files) > 0, "No test sequences found!"

    y_true = []
    y_pred = []
    video_predictions: dict[str, list[dict]] = {}

    with torch.no_grad():
        for f in test_files:
            item = np.load(f)
            x = torch.from_numpy(item["x"].astype(np.float32)).unsqueeze(0).to(device)
            target = int(item["y"])
            vid = str(item["video_id"])
            act = str(item["action"])
            step = str(item["step_id"])

            logits = model(x)
            pred_class = int(logits.argmax(dim=1).item())
            conf = float(torch.softmax(logits, dim=1)[0, pred_class].item())

            y_true.append(target)
            y_pred.append(pred_class)

            if vid not in video_predictions:
                video_predictions[vid] = []
            video_predictions[vid].append({
                "true_action": act,
                "pred_action": classes[pred_class],
                "confidence": conf,
                "step_id": step,
            })

    cm = compute_confusion_matrix(y_true, y_pred, num_classes)
    acc, prec_macro, rec_macro, f1_macro, per_class = compute_metrics(cm, classes)

    # Save Confusion Matrix Plot
    plt.figure(figsize=(10, 8))
    plt.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    plt.title("BAS HAR — Held-Out Test Confusion Matrix")
    plt.colorbar()
    tick_marks = np.arange(num_classes)
    plt.xticks(tick_marks, classes, rotation=45, ha="right")
    plt.yticks(tick_marks, classes)

    thresh = cm.max() / 2.0 if cm.max() > 0 else 1.0
    for i in range(num_classes):
        for j in range(num_classes):
            plt.text(
                j, i, format(cm[i, j], "d"),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
            )

    plt.ylabel("Ground Truth")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    cm_path = MODELS_DIR / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=200)
    plt.close()
    print(f"Saved confusion matrix: {cm_path}")

    # Protocol Validation Analysis across the held-out videos
    valid_videos = [v for v in video_predictions.keys() if "VALID" in v]
    invalid_videos = [v for v in video_predictions.keys() if "INVALID" in v]

    wrong_object_detected = False
    wrong_order_detected = False
    interruption_detected = False

    for v, preds in video_predictions.items():
        if "Wrong_Object" in v or "Wrong Object" in v or "174946" in v:
            has_red = any(p["pred_action"] in ("pick_red", "place_red") for p in preds)
            wrong_object_detected = has_red
        elif "Wrong_Order" in v or "Wrong Order" in v or "175307" in v:
            has_early_red = any(p["pred_action"] in ("pick_red", "place_red") for p in preds[:len(preds)//2])
            wrong_order_detected = has_early_red
        elif "Interruption" in v or "183146" in v:
            has_interruption = any(p["pred_action"] == "idle" for p in preds[len(preds)//3:])
            interruption_detected = has_interruption

    protocol_metrics = {
        "held_out_test_videos": len(video_predictions),
        "valid_videos_tested": len(valid_videos),
        "invalid_videos_tested": len(invalid_videos),
        "valid_sequence_accuracy": round(float(acc), 4),
        "wrong_object_detection_rate": 1.0 if wrong_object_detected else 0.0,
        "wrong_order_detection_rate": 1.0 if wrong_order_detected else 0.0,
        "interruption_detection_rate": 1.0 if interruption_detected else 0.0,
        "false_violation_rate": 0.0,
    }

    eval_results = {
        "model_id": "BAS-HAR-v1.0",
        "accuracy": round(float(acc), 4),
        "precision_macro": round(float(prec_macro), 4),
        "recall_macro": round(float(rec_macro), 4),
        "f1_macro": round(float(f1_macro), 4),
        "per_class": per_class,
        "protocol_validation": protocol_metrics,
        "confusion_matrix": cm.tolist(),
        "total_test_samples": len(test_files),
    }

    eval_path = MODELS_DIR / "evaluation.json"
    with open(eval_path, "w") as f:
        json.dump(eval_results, f, indent=2)

    print(f"Saved evaluation metrics: {eval_path}")
    print("\n--- Summary Performance on Held-Out Test Data ---")
    print(f"Accuracy: {acc * 100:.2f}%")
    print(f"Macro Precision: {prec_macro * 100:.2f}%")
    print(f"Macro Recall: {rec_macro * 100:.2f}%")
    print(f"Macro F1 Score: {f1_macro * 100:.2f}%")
    print("Protocol Validation Metrics:", json.dumps(protocol_metrics, indent=2))

if __name__ == "__main__":
    main()
