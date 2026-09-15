# ADR 012: Decoupled Multi-Class Protocol Object Perception and Tracking

## Status
Accepted

## Context
Validating BAS experiment protocols requires detecting specific scientific items (`tool_pipette_p1000`, `sample_cassette_a`, `centrifuge_tube_15ml`). Altering the primary person detector model to detect these objects risks breaking frozen Phase 1.1/1.2 crew detection weights and introducing class imbalance.

## Decision
1. **Secondary Object Detector Instance:** Introduce a modular `ObjectDetector` instance dedicated to protocol objects and tools, keeping the primary person detector frozen and certified.
2. **Unified Multi-Class ByteTracking:** Feed both crew detections and object detections into the multi-class `ByteTracker` implemented in Phase 1.2, assigning persistent spatial tracklet IDs across consecutive frames.
3. **Graceful Fallback:** If object detector inference is unconfigured or fails, the pipeline logs a contained error, falls back to skeletal-only predictions, and downgrades evidence to `PARTIAL_EVIDENCE` without pipeline halt.

## Consequences
### Positive
- Strict architectural decoupling: Person detection weights and certification remain untouched.
- Multi-object temporal persistence allows monitoring whether a pipette remains in the astronaut's hand across frames.
- Fault isolation: Subsystem failures in object detection do not degrade primary crew tracking.

### Negative / Trade-offs
- Slight increase in forward pass time when running the secondary object detector (asynchronous thread pool execution limits loop blocking).
