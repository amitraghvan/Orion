import React, { useState } from "react";
import { Hand } from "lucide-react";
import type {
  HandObservation,
  InteractionObservation,
  MultimodalActivityEvidence,
  ObjectObservation,
} from "../types/telemetry";

interface MultimodalIntelligenceProps {
  hands: HandObservation[];
  objects: ObjectObservation[];
  interactions: InteractionObservation[];
  multimodalEvidence: MultimodalActivityEvidence | null | undefined;
}

export const MultimodalIntelligence: React.FC<MultimodalIntelligenceProps> = ({
  hands,
  objects,
  interactions,
  multimodalEvidence,
}) => {
  const [showDetails, setShowDetails] = useState<boolean>(true);

  return (
    <div className="bg-space-900 border border-amber-500/40 rounded-lg p-4 shadow-lg flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
          <Hand className="w-4 h-4 text-amber-400" /> MULTIMODAL HOI & EVIDENCE INTELLIGENCE
        </h2>
        <div className="flex items-center gap-2">
          {multimodalEvidence && (
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                multimodalEvidence.evidence_state === "FULL_EVIDENCE"
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                  : multimodalEvidence.evidence_state === "PARTIAL_EVIDENCE"
                  ? "bg-amber-950 text-amber-400 border border-amber-800"
                  : multimodalEvidence.evidence_state === "CONFLICTING_EVIDENCE"
                  ? "bg-rose-950 text-rose-400 border border-rose-800 animate-pulse"
                  : "bg-space-850 text-slate-400 border border-space-700"
              }`}
            >
              {multimodalEvidence.evidence_state.replace("_", " ")}
            </span>
          )}
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-[10px] text-slate-400 hover:text-white font-mono px-2 py-0.5 rounded bg-space-800 border border-space-700 transition-colors"
          >
            {showDetails ? "COLLAPSE" : "EXPAND"}
          </button>
        </div>
      </div>

      {showDetails && (
        <div className="space-y-3 font-mono text-xs pt-1">
          {/* Hands Status Row */}
          <div className="grid grid-cols-2 gap-2">
            {["left", "right"].map((side) => {
              const h = hands.find((x) => x.side === side);
              const state = h?.state ?? "missing";
              const isObs = state === "observed";
              const isPart = state === "partial";
              return (
                <div
                  key={side}
                  className={`p-2 rounded border flex flex-col gap-1 transition-colors ${
                    isObs
                      ? "bg-amber-950/30 border-amber-700/60 text-amber-300"
                      : isPart
                      ? "bg-amber-950/10 border-amber-900/40 text-amber-500/80"
                      : "bg-space-850 border-space-800 text-slate-500"
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] uppercase font-bold">
                    <span>{side} HAND</span>
                    <span>{h ? `${(h.confidence * 100).toFixed(0)}%` : "0%"}</span>
                  </div>
                  <span className="text-[11px] font-bold uppercase">{state}</span>
                </div>
              );
            })}
          </div>

          {/* Physical Interaction Bindings */}
          <div className="bg-space-850 border border-space-700/60 rounded p-2.5 space-y-1.5">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-400">
              <span>Physical Interaction Bindings</span>
              <span className="text-amber-400 font-bold">{interactions.length} Active Link(s)</span>
            </div>
            {interactions.length > 0 ? (
              interactions.map((intr, idx) => (
                <div
                  key={`${intr.hand_id}-${intr.object_id}-${idx}`}
                  className="flex items-center justify-between text-[11px] py-1 border-b border-space-800/80 last:border-0"
                >
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="text-amber-300 font-bold">{intr.hand_id}</span>
                    <span className="text-slate-500">➔</span>
                    <span className="text-cyan-300 truncate max-w-[130px]">{intr.object_id}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                        intr.state === "grasping" || intr.state === "manipulating"
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : intr.state === "contact"
                          ? "bg-cyan-950 text-cyan-400 border border-cyan-800"
                          : intr.state === "approaching" || intr.state === "near"
                          ? "bg-amber-950 text-amber-400 border border-amber-800"
                          : "bg-space-800 text-slate-400"
                      }`}
                    >
                      {intr.state}
                    </span>
                    <span className="text-[10px] text-slate-400 font-bold">
                      {(intr.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-[11px] text-slate-500 py-1 text-center">
                No active hand-object interactions in proximity
              </div>
            )}
          </div>

          {/* Tracked Protocol Hardware Objects */}
          <div className="bg-space-850 border border-space-700/60 rounded p-2.5 space-y-1.5">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-400">
              <span>Tracked Protocol Hardware</span>
              <span className="text-cyan-400 font-bold">{objects.length} Object(s)</span>
            </div>
            {objects.length > 0 ? (
              <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                {objects.map((obj, idx) => (
                  <div
                    key={`${obj.object_id}-${idx}`}
                    className="bg-space-900 px-2 py-1 rounded border border-cyan-900/50 flex justify-between items-center"
                  >
                    <span className="text-cyan-300 font-bold truncate">{obj.class_name}</span>
                    <span className="text-slate-400">
                      #{obj.track_id ?? idx + 1} ({(obj.confidence * 100).toFixed(0)}%)
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[11px] text-slate-500 py-1 text-center">
                No protocol objects tracked in frame
              </div>
            )}
          </div>

          {/* Multimodal Sensory Quality Breakdown */}
          {multimodalEvidence && (
            <div className="bg-space-850 border border-space-700/60 rounded p-2.5 space-y-2">
              <div className="flex items-center justify-between text-[10px] uppercase text-slate-400">
                <span>Evidence Quality Level</span>
                <span
                  className={`font-bold px-1.5 py-0.5 rounded text-[10px] ${
                    multimodalEvidence.evidence_quality.overall === "HIGH"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : multimodalEvidence.evidence_quality.overall === "MEDIUM"
                      ? "bg-cyan-950 text-cyan-400 border border-cyan-800"
                      : multimodalEvidence.evidence_quality.overall === "LOW"
                      ? "bg-amber-950 text-amber-400 border border-amber-800"
                      : "bg-rose-950 text-rose-400 border border-rose-800"
                  }`}
                >
                  {multimodalEvidence.evidence_quality.overall}
                </span>
              </div>
              <div className="grid grid-cols-5 gap-1 text-[9px] text-center">
                <div className="bg-space-900 p-1 rounded border border-space-800">
                  <div className="text-slate-400">POSE</div>
                  <div className="text-white font-bold">
                    {(multimodalEvidence.evidence_quality.pose_quality * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="bg-space-900 p-1 rounded border border-space-800">
                  <div className="text-slate-400">ACTOR</div>
                  <div className="text-white font-bold">
                    {(multimodalEvidence.evidence_quality.actor_identity_quality * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="bg-space-900 p-1 rounded border border-space-800">
                  <div className="text-slate-400">HAND</div>
                  <div className="text-white font-bold">
                    {(multimodalEvidence.evidence_quality.hand_quality * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="bg-space-900 p-1 rounded border border-space-800">
                  <div className="text-slate-400">OBJECT</div>
                  <div className="text-white font-bold">
                    {(multimodalEvidence.evidence_quality.object_quality * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="bg-space-900 p-1 rounded border border-space-800">
                  <div className="text-slate-400">STABLE</div>
                  <div className="text-white font-bold">
                    {(multimodalEvidence.evidence_quality.temporal_stability * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
