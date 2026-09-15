import React from "react";
import {
  FileText,
  Crosshair,
  Target,
} from "lucide-react";
import { useTelemetryStore } from "../../store/telemetryStore";

export const EvidencePanel: React.FC = () => {
  const lastDecision = useTelemetryStore((state) => state.lastDecision);
  const activeViolation = useTelemetryStore((state) => state.activeViolation);
  const lastFrame = useTelemetryStore((state) => state.lastFrame);

  const status = activeViolation?.type ?? lastDecision?.status ?? "NOMINAL";
  const isViolation = activeViolation !== null || (status !== "NOMINAL" && status !== "IN_PROGRESS" && status !== "COMPLETED");

  const expected = activeViolation?.expected ??
    (Array.isArray(lastDecision?.expected_actions)
      ? lastDecision.expected_actions.join(", ")
      : lastDecision?.expected_action ?? "pick_yellow");

  const observed = activeViolation?.observed ?? lastDecision?.observed_action ?? "idle";
  const confidence = activeViolation?.confidence ??
    (lastDecision?.confidence ? Math.round(lastDecision.confidence * 100) : 94);

  const frameId = activeViolation?.evidence_frame ??
    lastDecision?.evidence?.frame_id ??
    `frame_${lastFrame?.frame_index ?? 0}`;

  const explanation = activeViolation?.explanation ??
    lastDecision?.explanation ??
    lastDecision?.message ??
    "Perception stream matches protocol expectations.";

  const interactions = lastFrame?.interactions ?? [];
  const detections = lastFrame?.detections ?? [];

  return (
    <div className="bg-space-900 border border-space-800 rounded-lg p-5 flex flex-col gap-3 shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold text-slate-100 tracking-wider uppercase">
            DECISION EVIDENCE & AUDIT LOG
          </h3>
        </div>
        <span
          className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider font-mono ${
            isViolation
              ? "bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse"
              : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
          }`}
        >
          {status}
        </span>
      </div>

      {/* Decision Rationale Cards */}
      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
        <div className="bg-space-950/70 border border-space-800 rounded p-2.5 flex flex-col gap-1">
          <span className="text-[10px] text-slate-400">EXPECTED PROTOCOL:</span>
          <span className="font-bold text-emerald-400 truncate">
            {expected.toUpperCase()}
          </span>
        </div>
        <div className="bg-space-950/70 border border-space-800 rounded p-2.5 flex flex-col gap-1">
          <span className="text-[10px] text-slate-400">OBSERVED PERCEPTION:</span>
          <span
            className={`font-bold truncate ${
              isViolation ? "text-rose-400" : "text-cyan-300"
            }`}
          >
            {observed.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-2 text-[11px] font-mono">
        <div className="bg-space-950/50 border border-space-850 rounded p-2 text-center">
          <span className="text-[9px] text-slate-500 block">CONFIDENCE</span>
          <span className="font-bold text-cyan-400">{confidence}%</span>
        </div>
        <div className="bg-space-950/50 border border-space-850 rounded p-2 text-center">
          <span className="text-[9px] text-slate-500 block">FRAME REF</span>
          <span className="font-bold text-slate-300 truncate block">#{frameId}</span>
        </div>
        <div className="bg-space-950/50 border border-space-850 rounded p-2 text-center">
          <span className="text-[9px] text-slate-500 block">HOI TARGETS</span>
          <span className="font-bold text-amber-400">{detections.length} objects</span>
        </div>
      </div>

      {/* Rationale Explanation Note */}
      <div className="bg-space-950 border border-space-800 rounded p-3 text-xs">
        <div className="flex items-center gap-1.5 text-slate-400 mb-1 text-[10px] font-semibold uppercase tracking-wider">
          <Target className="w-3 h-3 text-cyan-400" />
          <span>FSM DECISION RATIONALE:</span>
        </div>
        <p className="text-slate-300 leading-relaxed font-sans text-xs">
          {explanation}
        </p>
      </div>

      {/* Real-time HOI Evidence Clues */}
      {interactions.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {interactions.map((inter, i) => (
            <span
              key={i}
              className="px-2 py-0.5 rounded bg-space-800 border border-space-700 text-[10px] font-mono text-cyan-300 flex items-center gap-1"
            >
              <Crosshair className="w-2.5 h-2.5 text-amber-400" />
              {inter.state}: {(inter.confidence * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
