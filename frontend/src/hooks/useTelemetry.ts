import { useCallback, useEffect, useRef } from "react";
import { ensureStationToken, getAuthHeadersAsync } from "../services/auth";
import { useTelemetryStore } from "../store/telemetryStore";
import type { TelemetryFrame } from "../types/telemetry";

/**
 * Robust WebSocket telemetry hook for ORION BAS AI Copilot.
 * Connects to the backend WebSocket stream, automatically recovers on drops,
 * handles token authentication, throttles status updates, and feeds live frames into telemetryStore.
 */
export function useTelemetry(wsPath = "/ws/telemetry") {
  const isConnected = useTelemetryStore((state) => state.isConnected);
  const subsystemStatuses = useTelemetryStore((state) => state.subsystemStatuses);
  const experimentStatus = useTelemetryStore((state) => state.experimentStatus);
  const lastDecision = useTelemetryStore((state) => state.lastDecision);
  const {
    setConnected,
    updateFrame,
    updateSubsystemStatus,
    setExperimentStatus,
    setLastDecision,
    setCameraStatus,
    setAiStatus,
  } = useTelemetryStore();

  const statusDebounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isFetchingStatus = useRef<boolean>(false);

  const fetchStatus = useCallback(async () => {
    if (isFetchingStatus.current) return;
    isFetchingStatus.current = true;
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/experiments/status", {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        setExperimentStatus(data);
      } else if (res.status === 401 || res.status === 403) {
        // Token invalid or expired - refresh and retry once
        await ensureStationToken(true);
        const retryHeaders = await getAuthHeadersAsync();
        const retryRes = await fetch("/api/v1/experiments/status", { headers: retryHeaders });
        if (retryRes.ok) {
          const retryData = await retryRes.json();
          setExperimentStatus(retryData);
        }
      }

      
      // Authoritative camera status poll
      try {
        const camRes = await fetch("/api/v1/camera/status", { headers });
        if (camRes.ok) {
          const camData = await camRes.json();
          setCameraStatus(camData);
          if (!camData.connected) {
            setAiStatus("WAITING_FOR_CAMERA" as any);
          } else if (camData.state === "STREAMING") {
            setAiStatus("PROCESSING");
          } else {
            setAiStatus("READY");
          }
        }
      } catch {
        // Ignore camera status fetch error
      }
    } catch {
      // Ignore network errors in status poll
    } finally {
      isFetchingStatus.current = false;
    }
  }, [setExperimentStatus, setCameraStatus, setAiStatus]);

  const scheduleStatusRefresh = useCallback(() => {
    if (statusDebounceTimer.current) clearTimeout(statusDebounceTimer.current);
    statusDebounceTimer.current = setTimeout(() => {
      fetchStatus();
    }, 250);
  }, [fetchStatus]);

  // Periodic poll to maintain fresh camera and experiment state
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStatus();
    }, 2000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let isUnmounted = false;

    const connect = async () => {
      if (isUnmounted) return;
      const token = await ensureStationToken();
      if (isUnmounted) return;

      // Initial status sync
      fetchStatus();

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.port === "3000" ? "localhost:8000" : window.location.host;
      const wsUrl = token
        ? `${protocol}//${host}${wsPath}?token=${encodeURIComponent(token)}`
        : `${protocol}//${host}${wsPath}`;

      try {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
          if (!isUnmounted) {
            setConnected(true);
            updateSubsystemStatus("websocket", "HEALTHY");
            fetchStatus();
          }
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "TELEMETRY_FRAME") {
              const frame: TelemetryFrame = {
                type: data.type,
                station_id: data.station_id || "BAS-DEV-01",
                frame_index: data.frame_index ?? 0,
                timestamp_utc: data.timestamp_utc || new Date().toISOString(),
                source_id: data.source_id,
                width: data.width,
                height: data.height,
                detections: data.detections || [],
                poses: data.poses || [],
                tracks: data.tracks || [],
                activity: data.activity,
                activities: data.activities || [],
                top_activity: data.top_activity,
                hands: data.hands || [],
                objects: data.objects || [],
                interactions: data.interactions || [],
                multimodal_evidence: data.multimodal_evidence,
                metrics: data.metrics,
                pipeline_status: data.pipeline_status,
                image_jpeg: data.image_jpeg,
              };
              updateFrame(frame);
            } else if (data.type === "HEALTH_CHANGED" && data.subsystem) {
              updateSubsystemStatus(data.subsystem.toLowerCase(), data.status);
            } else if (data.type === "EXPERIMENT_STATUS") {
              setExperimentStatus(data);
            } else if (
              data.type === "ProtocolStateChanged" ||
              data.type === "StepTransitioned" ||
              data.type === "ExperimentUpdated" ||
              data.type === "NextStepRecommended"
            ) {
              scheduleStatusRefresh();
            } else if (data.type === "ProtocolDeviationDetected") {
              setLastDecision(data);
              scheduleStatusRefresh();
            }
          } catch {
            // Ignore parse errors or heartbeat pings
          }
        };

        socket.onclose = (ev) => {
          if (!isUnmounted) {
            setConnected(false);
            if (ev.code === 1008 || ev.code === 4003 || ev.code === 4403) {
              ensureStationToken(true);
            }
            reconnectTimeout = setTimeout(connect, 2000);
          }
        };

        socket.onerror = () => {
          if (socket && socket.readyState === WebSocket.OPEN) {
            socket.close();
          }
        };
      } catch {
        if (!isUnmounted) {
          reconnectTimeout = setTimeout(connect, 2000);
        }
      }
    };

    connect();

    return () => {
      isUnmounted = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (statusDebounceTimer.current) clearTimeout(statusDebounceTimer.current);
      if (socket) {
        socket.onclose = null;
        socket.onerror = null;
        socket.close();
      }
      setConnected(false);
    };
  }, [
    wsPath,
    setConnected,
    updateFrame,
    updateSubsystemStatus,
    setExperimentStatus,
    setLastDecision,
    fetchStatus,
    scheduleStatusRefresh,
  ]);

  return {
    isConnected,
    subsystemStatuses,
    experimentStatus,
    lastDecision,
    refreshStatus: fetchStatus,
  };
}
