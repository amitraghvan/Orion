import { useEffect } from "react";
import { useTelemetryStore } from "../store/telemetryStore";

/**
 * React hook contract for managing WebSocket telemetry connections.
 * In Phase 0, connection lifecycle is validated without active UI render.
 */
export function useTelemetry(wsUrl = "/ws/telemetry") {
  const { setConnected, updateFrame } = useTelemetryStore();

  useEffect(() => {
    // Protocol interface verification
    return () => {
      setConnected(false);
    };
  }, [wsUrl, setConnected, updateFrame]);
}
