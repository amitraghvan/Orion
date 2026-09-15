import React, { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Compass,
  FileCheck,
  Pause,
  Play,
  RefreshCw,
  Square,
} from "lucide-react";
import { getAuthHeadersAsync } from "../services/auth";
import type { ExperimentStatusPayload } from "../types/telemetry";

interface ProtocolCopilotProps {
  experimentStatus: ExperimentStatusPayload | null;
  lastDecision: any;
  refreshStatus: () => void;
}

export const ProtocolCopilot: React.FC<ProtocolCopilotProps> = ({
  experimentStatus,
  lastDecision,
  refreshStatus,
}) => {
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fsmState = experimentStatus?.fsm_state ?? "IDLE";
  const recommendation = experimentStatus?.recommendation;
  const isBlocked = fsmState === "BLOCKED";
  const isRunning =
    fsmState === "RUNNING" ||
    fsmState === "STEP_IN_PROGRESS" ||
    fsmState === "STEP_COMPLETED";

  const getFsmStateBadgeClass = (state: string) => {
    switch (state) {
      case "RUNNING":
      case "STEP_IN_PROGRESS":
        return "bg-emerald-950 text-emerald-400 border-emerald-700 animate-pulse";
      case "STEP_COMPLETED":
        return "bg-teal-950 text-teal-300 border-teal-700";
      case "BLOCKED":
        return "bg-rose-950 text-rose-400 border-rose-700 animate-bounce";
      case "PAUSED":
        return "bg-amber-950 text-amber-400 border-amber-700";
      case "ABORTED":
        return "bg-red-950 text-red-400 border-red-700";
      case "COMPLETED":
        return "bg-cyan-950 text-cyan-300 border-cyan-700";
      case "LOADED":
        return "bg-blue-950 text-blue-400 border-blue-700";
      default:
        return "bg-space-800 text-slate-400 border-space-700";
    }
  };

  const handleStart = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/experiments/start", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setActionError(err.detail || "Failed to start experiment");
      }
      refreshStatus();
    } catch (err: any) {
      setActionError(err?.message || "Network error starting run");
    } finally {
      setActionLoading(false);
    }
  };

  const handlePause = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/experiments/pause", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ reason: "Operator pause from HUD" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setActionError(err.detail || "Failed to pause");
      }
      refreshStatus();
    } catch (err: any) {
      setActionError(err?.message || "Network error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/experiments/resume", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ reason: "Operator resume from HUD" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setActionError(err.detail || "Failed to resume");
      }
      refreshStatus();
    } catch (err: any) {
      setActionError(err?.message || "Network error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAbort = async () => {
    if (!window.confirm("Confirm permanent abort of the active experiment run?")) return;
    setActionLoading(true);
    setActionError(null);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/experiments/abort", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ reason: "Operator abort from HUD" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setActionError(err.detail || "Failed to abort");
      }
      refreshStatus();
    } catch (err: any) {
      setActionError(err?.message || "Network error");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async (resolution: "PROCEED" | "RETRY") => {
    setActionLoading(true);
    setActionError(null);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/experiments/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ resolution }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setActionError(err.detail || `Failed to ${resolution.toLowerCase()} deviation`);
      }
      refreshStatus();
    } catch (err: any) {
      setActionError(err?.message || "Network error resolving deviation");
    } finally {
      setActionLoading(false);
    }
  };

  const steps = experimentStatus?.steps || [];

  return (
    <div className="bg-space-900 border border-cyan-700/70 rounded-lg p-4 shadow-xl flex flex-col">
      {/* Copilot Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Compass className="w-5 h-5 text-cyan-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-white">
            BAS EXPERIMENT INTELLIGENCE COPILOT
          </h2>
        </div>
        <span
          className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded border ${getFsmStateBadgeClass(
            fsmState
          )}`}
        >
          FSM: {fsmState}
        </span>
      </div>

      {/* Protocol Metadata & SHA-256 Digest */}
      <div className="bg-space-850 border border-space-700/60 rounded p-2.5 mb-3 font-mono text-xs flex flex-col gap-1.5">
        <div className="flex justify-between items-center">
          <span className="text-slate-400">Protocol ID:</span>
          <span className="text-cyan-300 font-bold">
            {experimentStatus?.experiment_id || "BAS-EXP-CRYSTAL-V1"}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-slate-400">Run ID:</span>
          <span className="text-slate-200">
            {experimentStatus?.run_id || "AWAITING OPERATOR INITIATION"}
          </span>
        </div>
        {experimentStatus?.protocol_hash && (
          <div className="flex justify-between items-center text-[10px]">
            <span className="text-slate-500">SHA-256:</span>
            <span
              className="text-emerald-400 font-mono truncate max-w-[220px]"
              title={experimentStatus.protocol_hash}
            >
              {experimentStatus.protocol_hash.substring(0, 16)}...
            </span>
          </div>
        )}
      </div>

      {/* Action Error Banner */}
      {actionError && (
        <div className="bg-rose-950/90 border border-rose-600 rounded p-2.5 mb-3 text-xs font-mono text-rose-200 flex items-center justify-between">
          <span>{actionError}</span>
          <button
            onClick={() => setActionError(null)}
            className="text-rose-400 font-bold text-xs ml-2 hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* Procedural Deviation Banner (when FSM is BLOCKED) */}
      {isBlocked && (
        <div className="bg-rose-950/80 border border-rose-600 rounded p-3 mb-3 text-xs font-mono text-rose-200 shadow-lg">
          <div className="flex items-center gap-2 font-bold mb-1 text-rose-400">
            <AlertTriangle className="w-4 h-4 text-rose-400 animate-pulse" />
            PROCEDURAL DEVIATION DETECTED
          </div>
          <p className="text-[11px] mb-2 leading-tight text-rose-300">
            {lastDecision?.message ??
              lastDecision?.explanation ??
              "Out-of-sequence or timeout condition detected. FSM execution blocked pending operator resolution."}
          </p>
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={() => handleResolve("PROCEED")}
              disabled={actionLoading}
              className="flex-1 bg-rose-600 hover:bg-rose-500 text-white font-bold py-1 px-2 rounded text-[11px] transition-colors flex items-center justify-center gap-1"
            >
              {actionLoading && <RefreshCw className="w-3 h-3 animate-spin" />} PROCEED WITH OVERRIDE
            </button>
            <button
              onClick={() => handleResolve("RETRY")}
              disabled={actionLoading}
              className="flex-1 bg-space-800 hover:bg-space-700 text-slate-200 font-bold py-1 px-2 rounded text-[11px] border border-space-600 transition-colors flex items-center justify-center gap-1"
            >
              {actionLoading && <RefreshCw className="w-3 h-3 animate-spin" />} RETRY STEP
            </button>
          </div>
        </div>
      )}

      {/* Scientific Next-Step Guidance */}
      <div className="bg-space-850 border border-cyan-800/40 rounded p-3 mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] font-mono uppercase text-cyan-400 font-bold flex items-center gap-1">
            <FileCheck className="w-3.5 h-3.5" /> SCIENTIFIC NEXT-STEP GUIDANCE
          </span>
          {recommendation && (
            <span className="text-[10px] font-mono text-slate-400">
              Step {recommendation.step_number} of {recommendation.total_steps}
            </span>
          )}
        </div>

        {recommendation ? (
          <div className="space-y-2">
            <div className="text-sm font-semibold text-white leading-snug">
              {recommendation.instruction_text}
            </div>
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Target Action:</span>
              <span className="text-cyan-300 px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 uppercase font-bold">
                {recommendation.expected_activity}
              </span>
            </div>

            {/* Nominal Duration Progress */}
            {recommendation.nominal_duration_seconds > 0 && (
              <div>
                <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
                  <span>Elapsed: {recommendation.elapsed_seconds.toFixed(0)}s</span>
                  <span>Nominal: {recommendation.nominal_duration_seconds}s</span>
                </div>
                <div className="w-full bg-space-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-cyan-400 h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(
                        (recommendation.elapsed_seconds /
                          recommendation.nominal_duration_seconds) *
                          100,
                        100
                      )}%`,
                    }}
                  />
                </div>
              </div>
            )}

            {/* Hazard Warnings */}
            {recommendation.hazard_warnings && recommendation.hazard_warnings.length > 0 && (
              <div className="bg-amber-950/40 border border-amber-800/60 rounded p-2 text-[10px] font-mono text-amber-300">
                {recommendation.hazard_warnings[0]}
              </div>
            )}
          </div>
        ) : (
          <div className="text-slate-500 text-xs font-mono text-center py-2">
            Experiment ready. Press START RUN to begin protocol guidance.
          </div>
        )}
      </div>

      {/* Genuine Protocol Steps Sequence - ZERO HARDCODED FAKE DATA */}
      <div className="space-y-1.5 mb-3 font-mono text-xs">
        <span className="text-[10px] uppercase tracking-wider text-slate-400">
          Procedure Steps Sequence
        </span>
        <div className="space-y-1">
          {steps.length > 0 ? (
            steps.map((st) => (
              <div
                key={st.step_id}
                className={`flex items-center justify-between p-2 rounded border ${
                  st.status === "ACTIVE"
                    ? "bg-cyan-950/60 border-cyan-500/80 text-white font-bold shadow-md"
                    : st.status === "COMPLETED"
                    ? "bg-space-850 border-emerald-800/40 text-slate-400"
                    : st.status === "ABORTED"
                    ? "bg-red-950/40 border-red-800/40 text-red-400"
                    : st.status === "PAUSED"
                    ? "bg-amber-950/40 border-amber-800/40 text-amber-400"
                    : "bg-space-850 border-space-700/40 text-slate-500"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-[10px] w-4 text-slate-400 font-bold">
                    #{st.step_number}
                  </span>
                  <span className="text-xs truncate max-w-[200px]" title={st.description}>
                    {st.expected_activity}
                  </span>
                </div>
                <div>
                  {st.status === "COMPLETED" ? (
                    <span className="text-emerald-400 flex items-center gap-1 text-[10px]">
                      <CheckCircle2 className="w-3 h-3" /> DONE
                    </span>
                  ) : st.status === "ACTIVE" ? (
                    <span className="text-cyan-400 text-[10px] animate-pulse font-bold">
                      ▶ ACTIVE
                    </span>
                  ) : st.status === "ABORTED" ? (
                    <span className="text-red-400 text-[10px] font-bold">ABORTED</span>
                  ) : st.status === "PAUSED" ? (
                    <span className="text-amber-400 text-[10px] font-bold">PAUSED</span>
                  ) : (
                    <span className="text-slate-600 text-[10px]">PENDING</span>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="text-slate-500 text-xs font-mono text-center py-3 border border-space-800 rounded bg-space-850">
              Synchronizing protocol specification with station engine...
            </div>
          )}
        </div>
      </div>

      {/* Operator Lifecycle Controls */}
      <div className="flex items-center gap-2 pt-1 font-mono text-xs">
        {!isRunning ? (
          <button
            onClick={handleStart}
            disabled={actionLoading}
            className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-1.5 px-3 rounded flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50 shadow-md"
          >
            {actionLoading ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}{" "}
            START RUN
          </button>
        ) : (
          <>
            <button
              onClick={handlePause}
              disabled={actionLoading}
              className="flex-1 bg-amber-600 hover:bg-amber-500 text-white font-bold py-1.5 px-2 rounded flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
            >
              {actionLoading ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Pause className="w-3.5 h-3.5" />
              )}{" "}
              PAUSE
            </button>
            <button
              onClick={handleResume}
              disabled={actionLoading}
              className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-1.5 px-2 rounded flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
            >
              {actionLoading ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}{" "}
              RESUME
            </button>
          </>
        )}
        <button
          onClick={handleAbort}
          disabled={actionLoading}
          className="bg-space-800 hover:bg-rose-900/60 text-rose-400 border border-rose-800 py-1.5 px-3 rounded flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
        >
          {actionLoading ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Square className="w-3.5 h-3.5" />
          )}{" "}
          ABORT
        </button>
      </div>
    </div>
  );
};
