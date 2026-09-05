# C4 Architectural Model — ORION BAS AI Copilot

## 1. System Context
The ORION system sits as an edge perception node inside the Bharatiya Antariksh Station (BAS) Science Module. It interfaces with:
- **Astronaut / Mission Specialists**: Receives procedural visual feedback via telemetry HUD and audio chimes.
- **Scientific Glovebox Cameras**: High-speed optical sensor input (GigE Vision / USB3).
- **Station Telemetry Bus**: Periodic synchronization of experiment metrics to ground station during telemetry communication windows.

## 2. Containers
- **Edge Perception Engine (`ai`)**: High-throughput TensorRT/ONNX runtime executing Detection, Pose, HOI, and HAR models.
- **Flight Mission Backend (`backend`)**: FastAPI async orchestrator managing persistence, event bus, and WebSocket streams.
- **Mission Control HUD (`frontend`)**: React/Tailwind telemetry dashboard running on cockpit tablets or station monitors.
- **Archival Storage (`data`)**: Radiation-tolerant NVMe partition storing video recordings and JSON manifests.

## 3. Components
- `CameraDriver`: Sensor abstraction with circular ring buffers.
- `EventBus`: Internal typed pub/sub bus dispatching telemetry events.
- `StateMachine`: Deterministic hierarchical state machine validating procedural experiment steps.
- `AudioAnnunciator`: Cooldown-enforced acoustic warning system.
