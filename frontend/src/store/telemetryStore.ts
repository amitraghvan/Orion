import { create } from "zustand";
import type {
  ExperimentStatusPayload,
  SubsystemStatus,
  TelemetryFrame,
} from "../types/telemetry";

export interface ProtocolViolationData {
  type: string;
  expected: string;
  observed: string;
  step_number: number | string;
  confidence: number;
  timestamp: string;
  explanation: string;
  evidence_frame?: string | null;
  recommended_recovery?: string;
}

export interface CameraStatusData {
  connected: boolean;
  state: "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "STREAMING" | "ERROR";
  source: string;
  device_index: number | null;
  width: number;
  height: number;
  fps: number;
  frame_id: number;
  last_frame_timestamp?: string | null;
  is_file?: boolean;
  dropped_frames?: number;
  error?: string | null;
}

export interface TelemetryState {
  isConnected: boolean;
  cameraStatus: CameraStatusData;
  aiStatus: "INITIALIZING" | "READY" | "PROCESSING" | "DEGRADED" | "ERROR";
  activeExperimentId: string | null;
  selectedExperiment: string;
  selectedVariant: string;
  selectedReplayPath: string | null;
  currentStepId: string | null;
  lastFrame: TelemetryFrame | null;
  subsystemStatuses: Record<string, SubsystemStatus>;
  experimentStatus: ExperimentStatusPayload | null;
  lastDecision: any | null;
  activeViolation: ProtocolViolationData | null;
  voiceStatus: "READY" | "ALERT_ACTIVE";
  recordingStatus: "IDLE" | "RECORDING";
  streamingStatus: "LOCAL" | "STREAMING" | "OFFLINE";
  modelInfo: {
    modelId: string;
    datasetVersion: string;
  };

  // Actions
  setConnected: (connected: boolean) => void;
  setCameraStatus: (status: Partial<CameraStatusData>) => void;
  setAiStatus: (status: "INITIALIZING" | "READY" | "PROCESSING" | "DEGRADED" | "ERROR") => void;
  setExperimentSelection: (experimentId: string, variant: string) => void;
  setSelectedReplay: (path: string | null) => void;
  updateFrame: (frame: TelemetryFrame) => void;
  updateSubsystemStatus: (subsystem: string, status: SubsystemStatus) => void;
  setExperimentStatus: (status: ExperimentStatusPayload) => void;
  setLastDecision: (decision: any) => void;
  setActiveViolation: (violation: ProtocolViolationData | null) => void;
  setVoiceStatus: (status: "READY" | "ALERT_ACTIVE") => void;
  setRecordingStatus: (status: "IDLE" | "RECORDING") => void;
  setStreamingStatus: (status: "LOCAL" | "STREAMING" | "OFFLINE") => void;
  reset: () => void;
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  isConnected: false,
  cameraStatus: {
    connected: false,
    state: "DISCONNECTED",
    source: "0",
    device_index: 0,
    width: 1280,
    height: 720,
    fps: 0,
    frame_id: 0,
    error: null,
  },
  aiStatus: "READY",
  activeExperimentId: "BAS-EXP-E01-A",
  selectedExperiment: "E01",
  selectedVariant: "A",
  selectedReplayPath: "/Users/amitkumar/Downloads/BAS_REAL_DATA/VALID/SP04/AP01.mp4",
  currentStepId: null,
  lastFrame: null,
  subsystemStatuses: {
    camera: "HEALTHY",
    ai_pipeline: "HEALTHY",
    pose_estimator: "HEALTHY",
    byte_tracker: "HEALTHY",
    temporal_har: "HEALTHY",
    protocol_engine: "HEALTHY",
    websocket: "HEALTHY",
    database: "HEALTHY",
  },
  experimentStatus: null,
  lastDecision: null,
  activeViolation: null,
  voiceStatus: "READY",
  recordingStatus: "IDLE",
  streamingStatus: "LOCAL",
  modelInfo: {
    modelId: "BAS-HAR-v1.0",
    datasetVersion: "BAS-DATA-v1.0.0",
  },

  setConnected: (connected) => set({ isConnected: connected }),
  setCameraStatus: (newStatus) =>
    set((state) => ({ cameraStatus: { ...state.cameraStatus, ...newStatus } })),
  setAiStatus: (status) => set({ aiStatus: status }),
  setExperimentSelection: (experimentId, variant) =>
    set({
      selectedExperiment: experimentId,
      selectedVariant: variant,
      activeExperimentId: `BAS-EXP-${experimentId.toUpperCase()}-${variant.toUpperCase()}`,
    }),
  setSelectedReplay: (path) => set({ selectedReplayPath: path }),
  updateFrame: (frame) => set({ lastFrame: frame }),
  updateSubsystemStatus: (subsystem, status) =>
    set((state) => ({
      subsystemStatuses: { ...state.subsystemStatuses, [subsystem]: status },
    })),
  setExperimentStatus: (status) =>
    set({
      experimentStatus: status,
      activeExperimentId: status.experiment_id,
      currentStepId: status.current_step?.step_id ?? null,
    }),
  setLastDecision: (decision) => {
    set({ lastDecision: decision });
    if (
      decision &&
      ["WRONG_OBJECT", "SKIPPED", "OUT_OF_SEQUENCE", "INTERRUPTED", "TIMEOUT", "INVALID_ACTION"].includes(
        decision.status || decision.deviation_type
      )
    ) {
      const vType = decision.status || decision.deviation_type;
      const expectedStr = Array.isArray(decision.expected_actions)
        ? decision.expected_actions.join(", ")
        : decision.expected_action || "Expected procedure step";
      const observedStr = decision.observed_action || "Observed deviation";
      set({
        activeViolation: {
          type: vType,
          expected: expectedStr,
          observed: observedStr,
          step_number: decision.step_number || 1,
          confidence: Math.round((decision.confidence || 0.91) * 100),
          timestamp: new Date().toISOString().substring(11, 19),
          explanation: decision.explanation || decision.message || "Protocol sequence violation detected",
          evidence_frame: decision.evidence?.frame_id ?? null,
          recommended_recovery: `Return to Step ${decision.step_number || 1} and repeat procedure`,
        },
      });
    }
  },
  setActiveViolation: (violation) => set({ activeViolation: violation }),
  setVoiceStatus: (status) => set({ voiceStatus: status }),
  setRecordingStatus: (status) => set({ recordingStatus: status }),
  setStreamingStatus: (status) => set({ streamingStatus: status }),
  reset: () =>
    set({
      isConnected: false,
      lastFrame: null,
      experimentStatus: null,
      lastDecision: null,
      activeViolation: null,
      voiceStatus: "READY",
      recordingStatus: "IDLE",
      streamingStatus: "LOCAL",
    }),
}));
