import React from "react";
import { Zap } from "lucide-react";
import type { ActivityPrediction } from "../types/telemetry";

interface ActionRecognitionProps {
  primaryActivity: ActivityPrediction | undefined;
}

export const ActionRecognition: React.FC<ActionRecognitionProps> = ({ primaryActivity }) => {
  return (
    <div className="bg-space-900 border border-cyan-800/50 rounded-lg p-4 shadow-lg flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2">
          <Zap className="w-4 h-4 text-cyan-400" /> LIVE ACTION RECOGNITION (ST-GCN)
        </h2>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
          T=32 / S=8
        </span>
      </div>

      {primaryActivity ? (
        <div className="space-y-2.5 font-mono text-xs">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] text-slate-400 uppercase">Classified Action</span>
              <div className="text-sm font-bold text-white uppercase tracking-wide">
                {primaryActivity.activity_name.replace("_", " ")}
              </div>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-slate-400 uppercase">Phase / Uncertainty</span>
              <div className="flex items-center gap-1.5 justify-end mt-0.5">
                <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                  {primaryActivity.phase ?? "UPDATE"}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded font-bold ${
                    primaryActivity.uncertainty_status === "NOMINAL"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : "bg-amber-950 text-amber-400 border border-amber-800"
                  }`}
                >
                  {primaryActivity.uncertainty_status ?? "NOMINAL"}
                </span>
              </div>
            </div>
          </div>

          {/* Confidence Meter */}
          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-slate-400">Confidence</span>
              <span className="text-cyan-400 font-bold">
                {(primaryActivity.confidence * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-space-800 rounded-full h-2 overflow-hidden border border-space-700">
              <div
                className="bg-cyan-400 h-full rounded-full transition-all duration-300"
                style={{ width: `${Math.min(primaryActivity.confidence * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Multi-Class Probability Distribution */}
          {primaryActivity.probabilities && (
            <div className="space-y-1 pt-1">
              <span className="text-[10px] text-slate-400">Class Softmax Probabilities</span>
              <div className="grid grid-cols-2 gap-1.5 text-[10px]">
                {Object.entries(primaryActivity.probabilities).map(([cls, prob]) => (
                  <div
                    key={cls}
                    className="bg-space-850 px-2 py-1 rounded border border-space-700/50 flex justify-between"
                  >
                    <span className="text-slate-300 truncate">{cls}</span>
                    <span className={prob > 0.3 ? "text-cyan-400 font-bold" : "text-slate-500"}>
                      {(prob * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-slate-500 text-xs text-center py-4 font-mono">
          Awaiting temporal sequence window (32 frames)...
        </div>
      )}
    </div>
  );
};
