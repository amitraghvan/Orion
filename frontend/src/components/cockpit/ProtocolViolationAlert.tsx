import React from "react";
import { AlertOctagon, RotateCcw, Volume2, XCircle } from "lucide-react";
import { useTelemetryStore } from "../../store/telemetryStore";
import { getAuthHeadersAsync } from "../../services/auth";

export const ProtocolViolationAlert: React.FC = () => {
  const activeViolation = useTelemetryStore((state) => state.activeViolation);
  const setActiveViolation = useTelemetryStore((state) => state.setActiveViolation);
  const setExperimentStatus = useTelemetryStore((state) => state.setExperimentStatus);

  if (!activeViolation) return null;

  const handleResolve = async (resolution: "PROCEED" | "RETRY" | "ABORT") => {
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/experiments/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ resolution }),
      });
      if (res.ok) {
        setActiveViolation(null);
        const statusRes = await fetch("/api/v1/experiments/status", { headers });
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          setExperimentStatus(statusData);
        }
      }
    } catch (err) {
      console.error("Failed to resolve violation:", err);
    }
  };

  return (
    <div className="bg-rose-950/80 border-2 border-rose-500 rounded-lg p-5 flex flex-col gap-4 shadow-glow-rose/40 animate-pulse">
      {/* Alert Header */}
      <div className="flex items-center justify-between border-b border-rose-500/30 pb-3">
        <div className="flex items-center gap-2 text-rose-300">
          <AlertOctagon className="w-6 h-6 text-rose-400" />
          <h3 className="text-sm font-black tracking-widest uppercase">
            ⚠ PROTOCOL VIOLATION DETECTED
          </h3>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/30 text-rose-200 border border-rose-400/40">
          {activeViolation.type}
        </span>
      </div>

      {/* Violation Breakdown Grid */}
      <div className="grid grid-cols-2 gap-3 bg-space-950/90 border border-rose-500/30 rounded p-3 text-xs">
        <div>
          <span className="text-[10px] text-slate-400 block mb-0.5">EXPECTED:</span>
          <span className="font-bold text-emerald-400 font-mono">
            {activeViolation.expected.toUpperCase()}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-slate-400 block mb-0.5">OBSERVED:</span>
          <span className="font-bold text-rose-400 font-mono">
            {activeViolation.observed.toUpperCase()}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-slate-400 block mb-0.5">STEP NUMBER:</span>
          <span className="font-mono text-slate-200">
            Step {activeViolation.step_number}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-slate-400 block mb-0.5">AI CONFIDENCE:</span>
          <span className="font-mono font-bold text-rose-300">
            {activeViolation.confidence}%
          </span>
        </div>
      </div>

      {/* Voice Alert Trigger Indicator */}
      <div className="flex items-center gap-2 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded px-3 py-2">
        <Volume2 className="w-4 h-4 text-amber-400 shrink-0 animate-bounce" />
        <span>🔊 Voice Alert Triggered: Astronaut safety & procedural advisory emitted.</span>
      </div>

      {/* Recovery Recommendation */}
      <div className="flex items-center justify-between text-xs text-slate-300">
        <span>
          <strong className="text-slate-100">RECOMMENDED:</strong>{" "}
          {activeViolation.recommended_recovery ?? "Return to previous step and repeat required operation."}
        </span>
      </div>

      {/* Operator Resolution Actions */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={() => handleResolve("RETRY")}
          className="flex-1 flex items-center justify-center gap-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded py-1.5 text-xs font-semibold tracking-wider transition"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          RETRY STEP
        </button>

        <button
          onClick={() => handleResolve("PROCEED")}
          className="flex-1 flex items-center justify-center gap-1.5 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 rounded py-1.5 text-xs font-semibold tracking-wider transition"
        >
          ACKNOWLEDGE & PROCEED
        </button>

        <button
          onClick={() => handleResolve("ABORT")}
          className="flex items-center justify-center gap-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 rounded px-3 py-1.5 text-xs font-semibold tracking-wider transition"
        >
          <XCircle className="w-3.5 h-3.5" />
          ABORT
        </button>
      </div>
    </div>
  );
};
