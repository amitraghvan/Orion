"""Prometheus metrics instrumentation for ORION BAS AI Copilot.

Air-gapped, sub-millisecond metrics collection for real-time perception, event dispatch,
database persistence, and telemetry WebSocket feeds.
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest

# Dedicated isolated registry to avoid collision in test/dev reloads
REGISTRY = CollectorRegistry(auto_describe=True)

# 1. Pipeline Frame Counters
FRAMES_RECEIVED_TOTAL = Counter(
    "orion_frames_received_total",
    "Total raw optical frames captured from camera driver",
    ["station_id"],
    registry=REGISTRY,
)

FRAMES_PROCESSED_TOTAL = Counter(
    "orion_frames_processed_total",
    "Total optical frames successfully processed through perception DAG",
    ["station_id"],
    registry=REGISTRY,
)

FRAMES_FAILED_TOTAL = Counter(
    "orion_frames_failed_total",
    "Total frames that encountered perception or hardware errors",
    ["station_id"],
    registry=REGISTRY,
)

# 2. Latency Gauges
INFERENCE_LATENCY_MS = Gauge(
    "orion_inference_latency_ms",
    "Latest inference execution latency in milliseconds by perception stage",
    ["stage"],
    registry=REGISTRY,
)

INFERENCE_LATENCY_AVG_MS = Gauge(
    "orion_inference_latency_avg_ms",
    "Rolling average perception pipeline latency in milliseconds",
    ["station_id"],
    registry=REGISTRY,
)

# 3. Observation & Persistence Counters
OBSERVATIONS_PUBLISHED_TOTAL = Counter(
    "orion_observations_published_total",
    "Total StructuredObservation events published to event bus",
    ["station_id"],
    registry=REGISTRY,
)

OBSERVATIONS_PERSISTED_TOTAL = Counter(
    "orion_observations_persisted_total",
    "Total audit and domain events successfully committed to database",
    ["station_id"],
    registry=REGISTRY,
)

# 4. Event Bus Counters
EVENT_BUS_EVENTS_TOTAL = Counter(
    "orion_event_bus_events_total",
    "Total typed events published through in-memory bus",
    ["event_type"],
    registry=REGISTRY,
)

EVENT_BUS_FAILURES_TOTAL = Counter(
    "orion_event_bus_failures_total",
    "Total subscriber exceptions caught and isolated in event bus",
    ["event_type"],
    registry=REGISTRY,
)

# 5. Telemetry WebSocket Metrics
WEBSOCKET_BROADCASTS_TOTAL = Counter(
    "orion_websocket_broadcasts_total",
    "Total telemetry payloads dispatched to connected WebSocket clients",
    registry=REGISTRY,
)

WEBSOCKET_CLIENTS = Gauge(
    "orion_websocket_clients",
    "Current active connected telemetry WebSocket subscribers",
    registry=REGISTRY,
)

# 6. Pipeline Errors Counter
PIPELINE_ERRORS_TOTAL = Counter(
    "orion_pipeline_errors_total",
    "Total unhandled exceptions caught by pipeline supervisor loop",
    ["stage"],
    registry=REGISTRY,
)


def get_latest_metrics() -> bytes:
    """Generate latest Prometheus exposition format text bytes."""
    return generate_latest(REGISTRY)
