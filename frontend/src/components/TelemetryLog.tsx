import React from "react";
import { Terminal } from "lucide-react";

export interface LogEntry {
  time: string;
  text: string;
  type: string;
}

interface TelemetryLogProps {
  logs: LogEntry[];
}

export const TelemetryLog: React.FC<TelemetryLogProps> = ({ logs }) => {
  return (
    <div className="bg-space-900 border border-space-700 rounded-lg p-4 shadow-lg flex-1 flex flex-col">
      <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
        <Terminal className="w-4 h-4 text-telemetry-400" /> MISSION TELEMETRY EVENT STREAM
      </h2>
      <div className="flex-1 overflow-y-auto max-h-40 space-y-1.5 font-mono text-[11px] pr-1">
        {logs.length > 0 ? (
          logs.map((log, idx) => (
            <div key={idx} className="flex items-start gap-2 text-slate-300">
              <span className="text-slate-500 shrink-0">{log.time}</span>
              <span
                className={
                  log.type === "protocol"
                    ? "text-rose-400 font-bold"
                    : log.type === "activity"
                    ? "text-cyan-400 font-medium"
                    : log.type === "detection"
                    ? "text-telemetry-400"
                    : "text-nominal"
                }
              >
                {log.text}
              </span>
            </div>
          ))
        ) : (
          <div className="text-slate-500 text-xs text-center py-4 font-mono">
            Listening for typed telemetry events from station bus...
          </div>
        )}
      </div>
    </div>
  );
};
