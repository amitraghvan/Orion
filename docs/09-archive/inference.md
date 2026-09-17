# ORION Multi-Backend Inference Pipeline

## 1. Modular Inference Architecture

ORION features an abstracted multi-backend perception pipeline designed to run on heterogeneous space station compute hardware (e.g., radiation-hardened x86 workstations, NVIDIA Jetson modules, or flight laptops).

```
   Raw Camera Frame (1280x720 BGR)
                  │
                  ▼
   ┌───────────────────────────────┐
   │ C++ VideoProcessor            │
   │ (Letterbox Resizing to 640x640│
   │  Bilinear SIMD / Normalization)
   └──────────────┬────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│ YOLOv11       │   │ YOLOv11-Pose  │
│ Object Det    │   │ Joint Tracker │
└───────┬───────┘   └───────┬───────┘
        │                   │
        │  [Detections]     │  [17 COCO Keypoints]
        ▼                   ▼
┌───────────────────────────────────┐
│ C++ / Python ByteTracker          │
│ Kalman Filtering & Trajectory ID  │
└─────────────────┬─────────────────┘
                  │
                  ▼
┌───────────────────────────────────┐
│ Hand-Object Interaction (HOI)     │
│ Wrist/Elbow Hand ROI Projection   │
│ 5-State Contact Machine           │
└─────────────────┬─────────────────┘
                  │
                  ▼
┌───────────────────────────────────┐
│ Sliding Window Temporal Buffer    │
│ (32 frames x 17 joints x 3 coords)│
└─────────────────┬─────────────────┘
                  │
                  ▼
┌───────────────────────────────────┐
│ ST-GCN Action Classifier          │
│ Calibrated Softmax Probabilities  │
│ Entropy Computation               │
└─────────────────┬─────────────────┘
                  │
                  ▼
   Calibrated Action & Confidence
```

---

## 2. Supported Execution Backends

### 2.1 PyTorch (`PyTorchBackend`)
- Supported models: `.pt` weight checkpoints.
- Acceleration devices:
  - `cuda`: NVIDIA Tensor Cores with automatic FP16 half-precision.
  - `mps`: Apple Metal Performance Shaders on Apple Silicon.
  - `cpu`: Optimized multi-threaded CPU inference.

### 2.2 ONNX Runtime (`ONNXBackend`)
- Supported models: `.onnx` exported graphs.
- Execution providers:
  - `CUDAExecutionProvider`
  - `CoreMLExecutionProvider`
  - `CPUExecutionProvider` (with AVX2/AVX-512 vectorization)

### 2.3 TensorRT (`TensorRTBackend`)
- Supported models: `.engine` compiled serializations.
- Target hardware: NVIDIA Ampere, Ada Lovelace, and Jetson Orin architectures.
- Benefits: Kernel auto-tuning, layer fusion, and INT8/FP16 quantization.

---

## 3. Export Scripts

Tools to convert PyTorch models to production deployment formats:
- **ONNX Export**:
  ```bash
  python scripts/export/export_onnx.py --model models/weights/yolo11n.pt --output models/onnx/yolo11n.onnx
  ```
- **TensorRT Compilation**:
  ```bash
  python scripts/export/build_tensorrt_engine.py --onnx models/onnx/yolo11n.onnx --output models/tensorrt/yolo11n.engine --fp16
  ```

---

## 4. Confidence & Entropy Calibration

To ensure zero false-positive step transitions in microgravity experiments, raw logits are calibrated:

1. **Softmax Output**:
   $$p_i = \frac{e^{z_i / T}}{\sum_{j=1}^C e^{z_j / T}}$$
   where $T$ is the temperature scaling parameter (default: 1.0).

2. **Predictive Entropy**:
   $$H(p) = -\sum_{i=1}^C p_i \ln(p_i)$$
   If $H(p) > 1.40$, the model's confidence distribution is too dispersed (uncertain), triggering safety hold state `STEP_UNCERTAIN`.
