import React, { useEffect, useState } from "react";
import {
  FileCode,
  Download,
  X,
  CheckCircle,
} from "lucide-react";
import { getAuthHeadersAsync } from "../../services/auth";

interface MissionLogModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MissionLogModal: React.FC<MissionLogModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [summary, setSummary] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen) return;
    const fetchSummary = async () => {
      setIsLoading(true);
      try {
        const headers = await getAuthHeadersAsync();
        const res = await fetch("/api/v1/experiments/summary", { headers });
        if (res.ok) {
          const data = await res.json();
          setSummary(data);
        }
      } catch (err) {
        console.error("Failed to load mission summary:", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSummary();
  }, [isOpen]);

  if (!isOpen) return null;

  const handleDownload = () => {
    if (!summary) return;
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(JSON.stringify(summary, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute(
      "download",
      `bas_mission_log_${summary.run_id || "latest"}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-space-900 border border-space-700 rounded-xl max-w-2xl w-full flex flex-col shadow-2xl overflow-hidden max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-space-800 bg-space-850">
          <div className="flex items-center gap-2">
            <FileCode className="w-5 h-5 text-cyan-400" />
            <h2 className="text-sm font-bold text-slate-100 tracking-wider uppercase">
              STRUCTURED MISSION AUDIT LOG
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-space-700 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex flex-col gap-4 font-mono text-xs">
          {isLoading ? (
            <div className="py-12 text-center text-slate-400">
              Retrieving structured telemetry audit log...
            </div>
          ) : summary ? (
            <>
              {/* Summary Status Banner */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-space-950 border border-space-800 rounded p-3">
                  <span className="text-[10px] text-slate-400 block mb-1">
                    RUN ID
                  </span>
                  <span className="font-bold text-cyan-400 truncate block">
                    {summary.run_id}
                  </span>
                </div>
                <div className="bg-space-950 border border-space-800 rounded p-3">
                  <span className="text-[10px] text-slate-400 block mb-1">
                    EXPERIMENT
                  </span>
                  <span className="font-bold text-slate-200 block">
                    {summary.experiment_id}
                  </span>
                </div>
                <div className="bg-space-950 border border-space-800 rounded p-3">
                  <span className="text-[10px] text-slate-400 block mb-1">
                    STEPS COMPLETE
                  </span>
                  <span className="font-bold text-emerald-400 block">
                    {summary.steps_completed} / {summary.total_steps}
                  </span>
                </div>
                <div className="bg-space-950 border border-space-800 rounded p-3">
                  <span className="text-[10px] text-slate-400 block mb-1">
                    TOTAL VIOLATIONS
                  </span>
                  <span
                    className={`font-bold block ${
                      summary.total_violations > 0
                        ? "text-rose-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {summary.total_violations}
                  </span>
                </div>
              </div>

              {/* System Metadata */}
              <div className="flex items-center justify-between px-3 py-2 rounded bg-space-950 border border-space-800 text-[11px] text-slate-400">
                <span>AI Model: <strong className="text-cyan-300">{summary.ai_model}</strong></span>
                <span>Dataset: <strong className="text-indigo-300">{summary.dataset_version}</strong></span>
                <span>FSM State: <strong className="text-slate-200">{summary.fsm_state}</strong></span>
              </div>

              {/* Violations List */}
              <div className="flex flex-col gap-2">
                <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                  RECORDED DEVIATIONS ({summary.violations?.length ?? 0}):
                </span>
                {summary.violations && summary.violations.length > 0 ? (
                  <div className="flex flex-col gap-2 max-h-48 overflow-y-auto pr-1">
                    {summary.violations.map((v: any, idx: number) => (
                      <div
                        key={idx}
                        className="bg-rose-950/30 border border-rose-500/40 rounded p-2.5 flex flex-col gap-1 text-[11px]"
                      >
                        <div className="flex items-center justify-between text-rose-300 font-bold">
                          <span>{v.status}</span>
                          <span className="text-[10px] text-slate-400">
                            {v.created_at ? v.created_at.substring(11, 19) : "--:--:--"}
                          </span>
                        </div>
                        <div className="text-slate-300">
                          {v.explanation || `Step ${v.step_id}: ${v.observed_action} vs ${v.expected_actions?.join(", ")}`}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 rounded bg-space-950 border border-space-800 text-center text-emerald-400 flex items-center justify-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    <span>Zero deviations recorded in this run. Full protocol adherence.</span>
                  </div>
                )}
              </div>

              {/* JSON Preview */}
              <div className="flex flex-col gap-1.5">
                <span className="text-[11px] font-bold text-slate-400 uppercase">
                  RAW STRUCTURED PAYLOAD:
                </span>
                <pre className="bg-space-950 p-3 rounded border border-space-800 text-[10px] text-cyan-300/80 overflow-x-auto max-h-40 font-mono">
                  {JSON.stringify(summary, null, 2)}
                </pre>
              </div>
            </>
          ) : (
            <div className="py-12 text-center text-slate-500">
              No active mission run data available.
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-space-800 bg-space-850">
          <span className="text-[11px] text-slate-400 font-mono">
            Complies with SIH26174 Structured Lightweight Audit Log Specification
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded text-xs font-semibold text-slate-300 hover:text-white bg-space-800 hover:bg-space-700 transition"
            >
              Close
            </button>
            <button
              onClick={handleDownload}
              disabled={!summary}
              className="flex items-center gap-2 px-4 py-1.5 rounded text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white transition disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              Download JSON Log
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
