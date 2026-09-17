"""Unit tests verifying Prometheus metrics instrumentation and cardinalities."""

import pytest

from orion.core.metrics import (
    EVENT_BUS_EVENTS_TOTAL,
    EVENT_BUS_FAILURES_TOTAL,
    FRAMES_FAILED_TOTAL,
    FRAMES_PROCESSED_TOTAL,
    FRAMES_RECEIVED_TOTAL,
    INFERENCE_LATENCY_AVG_MS,
    INFERENCE_LATENCY_MS,
    OBSERVATIONS_PERSISTED_TOTAL,
    OBSERVATIONS_PUBLISHED_TOTAL,
    PIPELINE_ERRORS_TOTAL,
    REGISTRY,
    WEBSOCKET_BROADCASTS_TOTAL,
    WEBSOCKET_CLIENTS,
    get_latest_metrics,
)


@pytest.mark.unit
def test_metrics_counters_increment() -> None:
    """Verify all pipeline counters increment and generate valid exposition."""
    station = "BAS-TEST-STATION"

    # Increment instruments
    FRAMES_RECEIVED_TOTAL.labels(station_id=station).inc()
    FRAMES_PROCESSED_TOTAL.labels(station_id=station).inc()
    FRAMES_FAILED_TOTAL.labels(station_id=station).inc()
    OBSERVATIONS_PUBLISHED_TOTAL.labels(station_id=station).inc()
    OBSERVATIONS_PERSISTED_TOTAL.labels(station_id=station).inc()
    EVENT_BUS_EVENTS_TOTAL.labels(event_type="FrameCaptured").inc()
    EVENT_BUS_FAILURES_TOTAL.labels(event_type="FrameCaptured").inc()
    PIPELINE_ERRORS_TOTAL.labels(stage="detection").inc()
    WEBSOCKET_BROADCASTS_TOTAL.inc()
    WEBSOCKET_CLIENTS.set(2)
    INFERENCE_LATENCY_MS.labels(stage="total").set(24.5)
    INFERENCE_LATENCY_AVG_MS.labels(station_id=station).set(22.1)

    raw_metrics = get_latest_metrics().decode("utf-8")

    assert "orion_frames_received_total" in raw_metrics
    assert "orion_frames_processed_total" in raw_metrics
    assert "orion_frames_failed_total" in raw_metrics
    assert "orion_observations_published_total" in raw_metrics
    assert "orion_observations_persisted_total" in raw_metrics
    assert "orion_websocket_broadcasts_total" in raw_metrics
    assert "orion_websocket_clients" in raw_metrics
    assert "orion_inference_latency_ms" in raw_metrics


@pytest.mark.unit
def test_zero_high_cardinality_labels() -> None:
    """Verify that metric collectors do not define high-cardinality label names."""
    forbidden_labels = {
        "frame_id",
        "timestamp",
        "experiment_id",
        "run_id",
        "correlation_id",
        "uuid",
    }

    for metric in REGISTRY.collect():
        for sample in metric.samples:
            label_keys = set(sample.labels.keys())
            overlap = label_keys.intersection(forbidden_labels)
            assert not overlap, (
                f"Metric {sample.name} contains high-cardinality label(s): {overlap}"
            )
