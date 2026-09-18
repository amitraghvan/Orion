# ORION Configuration System Audit 

---

## 1. Configuration Hierarchy & Precedence

ORION uses a layered, type-safe configuration system powered by Pydantic V2 Settings. Configuration values are resolved in the following order of precedence (highest to lowest):

```
1. CLI Arguments (e.g., --video, --camera, --protocol, --demo)
      │
      ▼
2. System Environment Variables (e.g., export ORION_CAMERA_SOURCE="1")
      │
      ▼
3. Local Environment File (.env.development / .env)
      │
      ▼
4. Master YAML Configuration File (configs/settings.yaml)
      │
      ▼
5. Pydantic Default Values (app/core/config.py / backend/src/orion/core/config.py)
```

---

## 2. Key Configuration Schemas

### 2.1 Camera Configuration (`camera`)
```yaml
camera:
  source: "0"                     # Device index (0, 1) or stream URL / video path
  width: 1280                     # Frame capture width
  height: 720                     # Frame capture height
  fps: 30                         # Target capture frame rate
  buffer_capacity: 2              # Bounded ring buffer capacity (maxlen=2)
  auto_reconnect: true            # Automatic recovery on hardware disconnection
  reconnect_backoff_seconds: [1, 2, 4] # Reconnection intervals
```

### 2.2 Model Configuration (`models`)
```yaml
models:
  device: "auto"                  # auto, mps, cuda, or cpu
  detection:
    path: "models/weights/yolo11n.pt"
    confidence_threshold: 0.25
    backend: "torchscript"
  pose:
    path: "models/weights/yolo11n-pose.pt"
    confidence_threshold: 0.25
    backend: "torchscript"
  activity:
    path: "models/bas_experiment/best.pt"
    window_size_frames: 32
    stride_frames: 8
    confidence_threshold: 0.65
    max_entropy_threshold: 1.40
```

### 2.3 Audio & Voice Configuration (`audio`)
```yaml
audio:
  voice_enabled: true             # Enable or disable speech alerts
  rate: 175                       # Speech rate in words per minute
  volume: 0.9                     # Audio output volume [0.0, 1.0]
  cooldown_seconds: 3.0           # Anti-spam duplicate utterance cooldown
```

### 2.4 Video Recording Configuration (`recording`)
```yaml
recording:
  enabled: true                   # Enable local session video recording
  output_dir: "recordings"        # Output directory for video and logs
  codec: "mp4v"                   # Video codec (mp4v, avc1)
  queue_maxsize: 120              # Max asynchronous frame queue size (4 seconds at 30 FPS)
```

### 2.5 Video Streaming Configuration (`streaming`)
```yaml
streaming:
  enabled: true                   # Enable IP network video streaming
  host: "127.0.0.1"               # Network interface binding (0.0.0.0 for LAN/station)
  port: 8080                      # Streaming server port
  jpeg_quality: 80                # JPEG compression quality [1-100]
```

---

## 3. Environment Variable Overrides

Any configuration parameter can be overridden via environment variables prefixed with `ORION_`:

| Environment Variable | Target Setting | Default Value | Description |
|---|---|---|---|
| `ORION_CAMERA_SOURCE` | `camera.source` | `"0"` | Set to device index or file path |
| `ORION_MODELS_DEVICE` | `models.device` | `"auto"` | Force `mps`, `cuda`, or `cpu` |
| `ORION_AUDIO_VOICE_ENABLED` | `audio.voice_enabled` | `true` | Mute speech synthesis |
| `ORION_STREAMING_ENABLED` | `streaming.enabled` | `true` | Enable or disable IP streaming |
| `ORION_STREAMING_PORT` | `streaming.port` | `8080` | Port for HTTP MJPEG server |
| `ORION_DATABASE_URL` | `database.url` | `sqlite+aiosqlite:///./data/orion_dev.db` | SQLite connection string |

---

## 4. Path Management & Isolation

All internal file paths are computed dynamically relative to the workspace root using [`app/core/paths.py`](file:///Users/amitkumar/Orion/app/core/paths.py):
- `paths.root_dir`: Orion repository root
- `paths.models_dir`: `models/`
- `paths.assets_dir`: `assets/`
- `paths.recordings_dir`: `recordings/`
- `paths.data_dir`: `data/`
- `paths.configs_dir`: `configs/`

This ensures that hardcoded absolute paths do not break deployment across diverse operating systems or user accounts.
