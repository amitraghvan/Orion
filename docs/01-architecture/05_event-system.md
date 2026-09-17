# ORION Event System & Internal Bus Architecture

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Architectural Role & Design Pattern

The ORION internal communication fabric is built upon a decoupled, asynchronous, in-memory **Publish-Subscribe Event Bus** implemented in [`backend/src/orion/events/event_bus.py`](file:///Users/amitkumar/Orion/backend/src/orion/events/event_bus.py) and [`app/core/event_bus.py`](file:///Users/amitkumar/Orion/app/core/event_bus.py).

### Key Architectural Characteristics:
- **Decoupling:** Perception workers, protocol validators, GUI dispatchers, audio synthesizers, and database loggers publish and subscribe without direct inter-component dependencies.
- **Error Isolation:** A subscriber exception (e.g., transient audio device error) is caught, logged, and isolated; it never halts the perception pipeline or drops video frames.
- **Thread Safety:** The event bus uses reentrant locks (`threading.RLock`) and asynchronous queues (`asyncio.Queue`) to allow safe dispatch across UI, perception, and network threads.
- **Synchronous & Asynchronous Bridging:** Supports both synchronous callbacks and asynchronous coroutine handlers.

---

## 2. Canonical Domain Event Taxonomy (16 Events)

All domain events inherit from `BaseEvent` in [`backend/src/orion/events/schemas.py`](file:///Users/amitkumar/Orion/backend/src/orion/events/schemas.py). Every event carries an immutable `event_id` (UUID4) and UTC `timestamp`.

| Event Type | Producer Subsystem | Consumer Subsystem | Payload Attributes |
|---|---|---|---|
| `FrameCaptured` | Camera Subsystem | Perception Coordinator | `frame_id`, `camera_id`, `width`, `height`, `channels` |
| `ObservationCaptured` | Perception Coordinator | Telemetry WS, GUI, Database | `frame_id`, `tracks_count`, `poses_count`, `hands_count`, `interactions_count`, `activities_count`, `pipeline_latency_ms` |
| `ObjectDetected` | YOLO Detector | Tracker, Telemetry | `frame_id`, `class_id`, `class_name`, `confidence`, `bbox` $[x_1, y_1, x_2, y_2]$ |
| `PoseDetected` | YOLO-Pose Estimator | Tracker, HOI, HAR Buffer | `frame_id`, `person_id`, `keypoints` $(17 \times 3)$, `mean_confidence` |
| `HandDetected` | Hand Extractor | HOI Engine, Telemetry | `frame_id`, `person_id`, `hand_id`, `side` (`left`/`right`), `bbox`, `center` $[x, y]$ |
| `InteractionDetected` | HOI Engine | Protocol Engine, Telemetry | `frame_id`, `person_id`, `hand_id`, `object_track_id`, `contact_state`, `distance_px`, `iou` |
| `ActionRecognized` | Temporal ST-GCN | Protocol Engine, GUI | `frame_id`, `track_id`, `action_name`, `confidence`, `entropy`, `window_size` |
| `StepStarted` | Protocol Engine | GUI, TTS, Database | `experiment_id`, `run_id`, `step_id`, `step_number`, `expected_actions`, `description` |
| `StepCompleted` | Protocol Engine | GUI, TTS, Database | `experiment_id`, `run_id`, `step_id`, `step_number`, `observed_action`, `confidence`, `duration_seconds` |
| `StepViolation` | Protocol Engine | GUI, TTS, Alerts Log | `experiment_id`, `run_id`, `step_id`, `violation_type` (`OUT_OF_SEQUENCE`, `WRONG_OBJECT`), `observed_action`, `explanation` |
| `ExperimentStarted` | Protocol Engine | UI, Recorder, Streamer | `experiment_id`, `run_id`, `protocol_path`, `total_steps`, `operator_id` |
| `ExperimentCompleted` | Protocol Engine | UI, Recorder, DB | `experiment_id`, `run_id`, `total_duration_seconds`, `successful_steps`, `violations_count` |
| `ExperimentFailed` | Protocol Engine | UI, Alerts, DB | `experiment_id`, `run_id`, `failed_step_id`, `error_message` |
| `VoiceRequested` | Protocol / Alerts | Offline TTS Engine | `text`, `priority` (1=High, 2=Medium, 3=Low), `force` (bool) |
| `RecordingStarted` | Experiment Recorder | UI, Storage Manager | `experiment_id`, `run_id`, `output_path`, `fps`, `resolution` |
| `RecordingStopped` | Experiment Recorder | UI, Storage Manager | `experiment_id`, `run_id`, `frames_written`, `file_size_bytes`, `duration_seconds` |

---

## 3. End-to-End Event Propagation Trace

Below is the concrete event flow during an astronaut step execution:

```
[Camera Hardware]
       │
       ▼ emits FrameCaptured (frame_id=1042)
[Coordinator]
       ├──► executes YOLO11n      ──► emits ObjectDetected ("yellow_box", conf=0.88)
       ├──► executes YOLO11n-pose ──► emits PoseDetected (person_id=1, 17 joints)
       ├──► executes HandExtract  ──► emits HandDetected (hand_id="p1_rh", side="right")
       ├──► executes HOI Engine   ──► emits InteractionDetected (MANIPULATE, "yellow_box")
       ├──► executes ST-GCN HAR   ──► emits ActionRecognized ("pick_yellow", conf=0.89, H=0.24)
       │
       ▼ emits ObservationCaptured (metrics={pipeline_latency_ms: 48.2})
[Protocol Service]
       │ evaluates ActionRecognized against Step 1 (Expected: "pick_yellow")
       │
       ├──► Step satisfies invariants & debounce streak (2/2)
       ├──► Advances FSM to Step 2
       │
       ├──► emits StepCompleted (step_number=1, observed_action="pick_yellow")
       │         └──► Database writes step record to SQLite `steps` table
       │         └──► GUI Dashboard updates checklist widget
       │
       ├──► emits VoiceRequested ("Step 1 completed. Please perform Step 2.", priority=3)
       │         └──► TTSEngine synthesizes speech utterance via offline audio device
       │
       └──► emits StepStarted (step_number=2, description="Place Yellow Box")
                 └──► NextStepEngine updates dashboard guidance banner
```
