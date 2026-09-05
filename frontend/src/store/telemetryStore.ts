import { create } from "zustand";
import type { SubsystemStatus, TelemetryFrame } from "../types/telemetry";

export interface TelemetryState {
  isConnected: boolean;
  activeExperimentId: string | null;
  currentStepId: string | null;
  lastFrame: TelemetryFrame | null;
  subsystemStatuses: Record<string, SubsystemStatus>;

  // Actions
  setConnected: (connected: boolean) => void;
  setExperiment: (experimentId: string, stepId: string) => void;
  updateFrame: (frame: TelemetryFrame) => void;
  updateSubsystemStatus: (subsystem: string, status: SubsystemStatus) => void;
  reset: () => void;
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  isConnected: false,
  activeExperimentId: null,
  currentStepId: null,
  lastFrame: null,
  subsystemStatuses: {},

  setConnected: (connected) => set({ isConnected: connected }),
  setExperiment: (experimentId, stepId) =>
    set({ activeExperimentId: experimentId, currentStepId: stepId }),
  updateFrame: (frame) => set({ lastFrame: frame }),
  updateSubsystemStatus: (subsystem, status) =>
    set((state) => ({
      subsystemStatuses: { ...state.subsystemStatuses, [subsystem]: status },
    })),
  reset: () =>
    set({
      isConnected: false,
      activeExperimentId: null,
      currentStepId: null,
      lastFrame: null,
      subsystemStatuses: {},
    }),
}));
