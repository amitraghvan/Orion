import { describe, it, expect } from "vitest";
import { getAuthHeaders, setAuthToken } from "./services/auth";
import { useTelemetryStore } from "./store/telemetryStore";
import type { TelemetryFrame } from "./types/telemetry";

describe("Telemetry & Auth Service", () => {
  it("manages station tokens and generates Bearer auth headers", () => {
    setAuthToken("station-test-token-12345");
    const headers = getAuthHeaders();
    expect(headers.Authorization).toBe("Bearer station-test-token-12345");
  });

  it("updates and stores live telemetry frames in telemetryStore", () => {
    const mockFrame: TelemetryFrame = {
      type: "TELEMETRY_FRAME",
      station_id: "BAS-DEV-01",
      frame_index: 42,
      timestamp_utc: new Date().toISOString(),
      detections: [],
      poses: [],
      image_jpeg: "base64encodedjpegdata",
      metrics: {
        camera_latency_ms: 1.2,
        detection_latency_ms: 5.0,
        pose_latency_ms: 4.2,
        tracking_latency_ms: 0.8,
        pipeline_latency_ms: 11.2,
        fps: 29.8,
        dropped_frames_total: 0,
      },
    };

    useTelemetryStore.getState().updateFrame(mockFrame);
    const stored = useTelemetryStore.getState().lastFrame;
    expect(stored?.frame_index).toBe(42);
    expect(stored?.image_jpeg).toBe("base64encodedjpegdata");
    expect(stored?.metrics?.fps).toBe(29.8);
  });

  it("updates subsystem statuses in telemetryStore", () => {
    useTelemetryStore.getState().updateSubsystemStatus("camera", "HEALTHY");
    useTelemetryStore.getState().updateSubsystemStatus("detector", "HEALTHY");

    const statuses = useTelemetryStore.getState().subsystemStatuses;
    expect(statuses.camera).toBe("HEALTHY");
    expect(statuses.detector).toBe("HEALTHY");
  });
});
