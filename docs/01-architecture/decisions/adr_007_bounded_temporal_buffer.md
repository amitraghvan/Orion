# Architectural Decision Record (ADR) 007: Per-Track Bounded Temporal Feature Buffer & Stale Track Eviction

## Status
**ACCEPTED** (2026-09-08)

## Context
Temporal models require a continuous sliding window of frames ($T=32$) sampled at regular strides ($S=8$). When multiple astronauts are in the glovebox field of view, or when astronauts step away, leave the frame, or return, unmanaged queues can cause:
1. Cross-person temporal data mixing (concatenating Person A's arm movement with Person B's motion).
2. Unbounded memory growth from stale, lost tracks remaining in memory indefinitely.
3. Unregulated inference triggering on every frame, causing unnecessary CPU saturation.

## Decision
1. Implement `TemporalFeatureBuffer` keyed strictly by persistent `track_id` from ByteTrack.
2. Bound each track queue with a `collections.deque(maxlen=window_size)`.
3. Trigger classification only on configurable stride boundaries once a window is filled.
4. Implement automatic stale-track eviction: Any `track_id` not observed for `stale_timeout_frames` (default: 30) has its buffer purged.
5. Track keypoint quality state explicitly (`OBSERVED`, `INTERPOLATED`, `HELD`, `INVALID`) with confidence penalties rather than blind interpolation.

## Consequences
- **Positive**: Strict multi-person isolation. Guaranteed zero memory leaks over multi-hour continuous execution. Deterministic sequence replay.
- **Negative**: Reappearing tracks require $T$ frames of warmup before emitting nominal predictions.
