import React, { useState } from "react";
import {
  CheckCircle2,
  Circle,
  Play,
  Pause,
  Square,
  Sparkles,
} from "lucide-react";
import { getAuthHeadersAsync } from "../../services/auth";
import { useTelemetryStore } from "../../store/telemetryStore";

const EXPERIMENTS = [
  { id: "E01", name: "E01 — Detecting Colour" },
  { id: "E02", name: "E02 — Interchanging Boxes" },
  { id: "E03", name: "E03 — Overlapping Boxes" },
  { id: "E04", name: "E04 — Moving" },
  { id: "E05", name: "E05 — In Container" },
];

export const ExperimentStatusPanel: React.FC = () => {
  const selectedExperiment = useTelemetryStore((state) => state.selectedExperiment);
  const selectedVariant = useTelemetryStore((state) => state.selectedVariant);
  const experimentStatus = useTelemetryStore((state) => state.experimentStatus);
  const setExperimentSelection = useTelemetryStore((state) => state.setExperimentSelection);
  const setExperimentStatus = useTelemetryStore((state) => state.setExperimentStatus);
  const lastDecision = useTelemetryStore((state) => state.lastDecision);

  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleSelectExperiment = async (expId: string, varId: string) => {
    setExperimentSelection(expId, varId);
    setIsLoading(true);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/experiments/select", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ experiment_id: expId, variant: varId }),
      });
      if (res.ok) {
        // Refresh status
        const statusRes = await fetch("/api/v1/experiments/status", { headers });
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          setExperimentStatus(statusData);
        }
      }
    } catch (err) {
      console.error("Failed to select experiment:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleControl = async (action: "start" | "pause" | "resume" | "abort") => {
    setIsLoading(true);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch(`/api/v1/experiments/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ reason: `Operator ${action} command` }),
      });
      if (res.ok) {
        const statusRes = await fetch("/api/v1/experiments/status", { headers });
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          setExperimentStatus(statusData);
        }
      }
    } catch (err) {
      console.error(`Failed ${action} command:`, err);
    } finally {
      setIsLoading(false);
    }
  };

  const fsmState = experimentStatus?.fsm_state ?? "LOADED";
  const currentStep = experimentStatus?.current_step;
  const currentStepNum = currentStep?.step_number ?? 1;
  const steps: any[] = (experimentStatus as any)?.specification?.steps ?? (experimentStatus?.steps as any[]) ?? [
    { step_number: 1, step_id: "S01", description: "Pick Yellow Box", expected_actions: ["pick_yellow"] },
    { step_number: 2, step_id: "S02", description: "Place Yellow Box", expected_actions: ["place_yellow"] },
    { step_number: 3, step_id: "S03", description: "Pick Red Box", expected_actions: ["pick_red"] },
    { step_number: 4, step_id: "S04", description: "Place Red Box", expected_actions: ["place_red"] },
  ];

  const detectedAction = lastDecision?.observed_action ?? "idle";
  const confidence = lastDecision?.confidence
    ? Math.round(lastDecision.confidence * 100)
    : 92;

  const isViolation = lastDecision?.status === "WRONG_OBJECT" || fsmState === "BLOCKED";

  return (
    <div className="bg-space-900 border border-space-800 rounded-lg p-5 flex flex-col gap-4 shadow-xl">
      {/* Header & Selectors */}
      <div className="flex flex-col gap-3 pb-3 border-b border-space-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-400" />
            <h2 className="text-xs font-bold text-slate-100 tracking-wider uppercase">
              EXPERIMENT COPILOT
            </h2>
          </div>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
              isViolation
                ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse"
                : fsmState === "COMPLETED"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
            }`}
          >
            {isViolation ? "⚠ PROTOCOL VIOLATION" : fsmState}
          </span>
        </div>

        {/* Experiment & Variant Dropdowns */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[10px] font-medium text-slate-400 block mb-1">
              EXPERIMENT
            </label>
            <select
              value={selectedExperiment}
              onChange={(e) => handleSelectExperiment(e.target.value, selectedVariant)}
              disabled={isLoading}
              className="w-full bg-space-800 border border-space-700 rounded px-2.5 py-1.5 text-xs text-slate-100 font-medium focus:outline-none focus:border-cyan-500"
            >
              {EXPERIMENTS.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[10px] font-medium text-slate-400 block mb-1">
              VARIANT
            </label>
            <select
              value={selectedVariant}
              onChange={(e) => handleSelectExperiment(selectedExperiment, e.target.value)}
              disabled={isLoading}
              className="w-full bg-space-800 border border-space-700 rounded px-2.5 py-1.5 text-xs text-slate-100 font-medium focus:outline-none focus:border-cyan-500"
            >
              <option value="A">Variant A</option>
              <option value="B">Variant B</option>
            </select>
          </div>
        </div>

        {/* Run Controls */}
        <div className="flex items-center gap-2 pt-1">
          {fsmState === "RUNNING" || fsmState === "STEP_IN_PROGRESS" ? (
            <button
              onClick={() => handleControl("pause")}
              disabled={isLoading}
              className="flex-1 flex items-center justify-center gap-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded py-1.5 text-xs font-semibold tracking-wider transition"
            >
              <Pause className="w-3.5 h-3.5" />
              PAUSE
            </button>
          ) : (
            <button
              onClick={() => handleControl("start")}
              disabled={isLoading}
              className="flex-1 flex items-center justify-center gap-1.5 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 rounded py-1.5 text-xs font-semibold tracking-wider transition"
            >
              <Play className="w-3.5 h-3.5" />
              START EXPERIMENT
            </button>
          )}

          <button
            onClick={() => handleControl("abort")}
            disabled={isLoading || fsmState === "IDLE"}
            className="flex items-center justify-center gap-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 rounded px-3 py-1.5 text-xs font-semibold tracking-wider transition"
          >
            <Square className="w-3.5 h-3.5" />
            ABORT
          </button>
        </div>
      </div>

      {/* Step Progress Checklist */}
      <div className="flex flex-col gap-2">
        <span className="text-[10px] font-semibold text-slate-400 tracking-wider uppercase">
          PROTOCOL SEQUENCE PROGRESS
        </span>
        <div className="grid grid-cols-1 gap-1.5">
          {steps.map((s: any, idx: number) => {
            const stepNum = s.step_number ?? idx + 1;
            const isDone = fsmState === "COMPLETED" || stepNum < currentStepNum;
            const isCurrent = stepNum === currentStepNum && fsmState !== "COMPLETED";

            return (
              <div
                key={s.step_id || idx}
                className={`flex items-center justify-between p-2 rounded text-xs transition border ${
                  isCurrent
                    ? isViolation
                      ? "bg-rose-500/10 border-rose-500/40 text-rose-200"
                      : "bg-cyan-500/10 border-cyan-500/40 text-cyan-200 shadow-glow-cyan/20"
                    : isDone
                    ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-300"
                    : "bg-space-800/40 border-space-700/40 text-slate-400"
                }`}
              >
                <div className="flex items-center gap-2">
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : isCurrent ? (
                    <span className="w-3 h-3 rounded-full bg-cyan-400 animate-ping shrink-0" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-500 shrink-0" />
                  )}
                  <span className="font-semibold text-[11px]">
                    STEP {stepNum}: {s.description || s.step_id}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">
                  {isDone ? "DONE" : isCurrent ? (isViolation ? "DEVIATION" : "ACTIVE") : "PENDING"}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Real-time AI Inference Card */}
      <div className="bg-space-950 border border-space-800 rounded p-3 flex flex-col gap-2">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400">CURRENT STEP:</span>
          <span className="font-bold text-slate-200">
            {currentStep?.description ?? "Step 1: Pick Yellow Box"}
          </span>
        </div>

        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400">DETECTED ACTION:</span>
          <span className="font-mono font-bold text-cyan-300 uppercase">
            {detectedAction.replace("_", " ")}
          </span>
        </div>

        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-400">AI CONFIDENCE:</span>
          <div className="flex items-center gap-2">
            <div className="w-20 h-1.5 rounded-full bg-space-800 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-300"
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className="font-mono font-bold text-emerald-400">
              {confidence}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
