# Architectural Decision Record (ADR) 004: Event Taxonomy & Transient Streaming vs Durable Storage Decoupling

## Status
**ACCEPTED** (2026-09-08)

## Context
ORION produces two fundamentally distinct categories of events:
1. **Transient High-Frequency Telemetry**: Raw sensor frames, per-frame bounding boxes, keypoint poses, and instantaneous FPS metrics emitted at 30 Hz (90–120 events/sec).
2. **Durable Domain Audit Events**: System state changes, experiment procedure step transitions, safety alerts, activity classifications, and recording milestones emitted at ~0.01–1 Hz.

Subscribing SQLite persistence indiscriminately to `BaseEvent` caused database write amplification of ~324,000 records/hour, introducing SQLite lock contention, disk space exhaustion on spaceborne solid-state drives, and write queue bloat.

## Decision
1. Establish a strict architectural boundary between Transient Telemetry and Durable Events.
2. High-frequency telemetry events (`FrameCaptured`, `DetectionCompleted`, `PoseCompleted`, `TELEMETRY_FRAME`) are routed exclusively to in-memory listeners and WebSocket client feeds.
3. Durable events (`AlertRaised`, `HealthChanged`, `ExperimentUpdated`, `ActivityRecognized`, `RecordingStarted`, `RecordingStopped`) are subscribed to `EventPersistenceSubscriber` for permanent SQLite auditing.
4. WebSocket client feeds use bounded per-client queues (`maxsize=16`) with drop-oldest policies for transient frames, ensuring slow clients cannot backpressure the perception pipeline or degrade mission control responsiveness.

## Consequences
- **Positive**: Eliminates database flooding and disk exhaustion. Telemetry streaming operates with sub-5ms fanout latency. Audit log retains high signal-to-noise ratio.
- **Negative**: Historical raw bounding box trajectories are not retrievable from SQLite without explicit recording sessions enabled.
