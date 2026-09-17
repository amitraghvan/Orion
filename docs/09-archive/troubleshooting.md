# ORION Operational Troubleshooting & Diagnostics

## 1. Camera & Video Sensor Issues

### Symptom: Black video preview or `CameraOpenError`
- **macOS Permissions**:
  Go to *System Settings* > *Privacy & Security* > *Camera* and ensure your terminal emulator or Python runtime has camera permissions granted.
- **Wrong Device Index**:
  Check `config/camera.yaml`. If your external USB glovebox camera is index 1, change:
  ```yaml
  source: "1"
  ```
- **File Loop Testing**:
  To test without a physical camera, point the source to the included sample replay:
  ```yaml
  source: "assets/sample_replay.mp4"
  ```

---

## 2. C++ Engine & Python Fallback

### Symptom: `ModuleNotFoundError: No module named 'orion_native'`
- The native C++ extension has not been compiled or is missing from the working directory.
- **Resolution**:
  Run CMake rebuild:
  ```bash
  cmake -B build -S . -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE=.venv/bin/python
  cmake --build build --config Release -j
  cp build/orion_native*.so .   # On Windows: Copy-Item build\Release\orion_native*.pyd .\
  ```
- **Fallback Mode**:
  ORION has automated graceful degradation. If `orion_native` is absent, the system automatically falls back to OpenCV video capture and pure Python ByteTracker tracking.

---

## 3. Audio & Speech Synthesis

### Symptom: No spoken voice guidance during step transitions
- **macOS**: Ensure system sound is not muted. macOS uses native `NSSS` voice drivers via `pyttsx3`.
- **Windows**: Windows uses SAPI5. Ensure the Windows Speech engine is installed.
- **Config Check**: Verify `config/config.yaml` has `voice_enabled: true`.

---

## 4. Model Loading & Inference Failures

### Symptom: CUDA Out of Memory or TensorRT error
- Set device to `"cpu"` in `config/models.yaml` for stable fallback:
  ```yaml
  detection:
    device: "cpu"
  pose:
    device: "cpu"
  activity:
    device: "cpu"
  ```
- On Apple Silicon, verify MPS is enabled:
  ```yaml
  device: "mps"
  ```
