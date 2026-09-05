# WebSocket Telemetry Protocol Specification

## Endpoint
`/ws/telemetry`

## Frame Format
Every message pushed over WebSocket contains a structured JSON telemetry frame matching `TelemetryFrame`:
```json
{
  "station_id": "BAS-SCIENCE-NODE-01",
  "frame_index": 14205,
  "timestamp_utc": "2026-03-15T12:00:00.123456Z",
  "detections": [
    {
      "class_id": 1,
      "class_name": "pipette",
      "confidence": 0.94,
      "box": { "x_min": 0.32, "y_min": 0.45, "x_max": 0.41, "y_max": 0.62 },
      "track_id": 7
    }
  ],
  "poses": [],
  "activity": {
    "activity_name": "pipette_aspiration",
    "confidence": 0.88,
    "is_nominal": true
  }
}
```
In Phase 0, connections are acknowledged with a status code indicating runtime non-implementation.
