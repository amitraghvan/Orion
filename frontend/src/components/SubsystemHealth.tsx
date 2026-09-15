import React, { useEffect, useState } from "react";
import { Cpu } from "lucide-react";
import type { SubsystemStatus } from "../types/telemetry";

interface SubsystemHealthProps {
  subsystemStatuses: Record<string, SubsystemStatus>;
  isConnected: boolean;
}

export const SubsystemHealth: React.FC<SubsystemHealthProps> = ({
  subsystemStatuses,
  isConnected,
}) => {
  const [backendHealth, setBackendHealth] = useState<{
    status: string;
    warehouse_connected: boolean;
    trust_score: number;
    details?: Record<string, string>;
  } | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("/api/v1/health");
        if (res.ok) {
          const data = await res.json();
          setBackendHealth(data);
        }
      } catch {
        setBackendHealth(null);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 3000);
    return () => clearInterval(interval);
  }, []);

  const subsystems = [
    { name: "Camera", key: "camera" },
    { name: "Pipeline", key: "pipeline" },
    { name: "Detector", key: "detector" },
    { name: "Pose", key: "pose" },
    { name: "ST-GCN", key: "har_model" },
    { name: "EventBus", key: "event_bus" },
    { name: "Database", key: "database" },
    { name: "Persist", key: "persistence" },
    { name: "Protocol", key: "protocol" },
    { name: "WebSocket", key: "websocket" },
  ];

  return (
    <div className="bg-space-900 border border-space-700 rounded-lg p-4 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-telemetry-400" /> SUBSYSTEM HEALTH MATRIX
        </h2>
        {backendHealth && (
          <span className="text-[10px] font-mono text-emerald-400">
            TRUST: {backendHealth.trust_score.toFixed(1)}% | {backendHealth.status}
          </span>
        )}
      </div>

      <div className="grid grid-cols-5 gap-2 text-xs font-mono">
        {subsystems.map((sub) => {
          let status: string =
            backendHealth?.details?.[sub.key] ||
            subsystemStatuses[sub.key] ||
            (sub.key === "websocket" && isConnected ? "HEALTHY" : "");

          if (!status) {
            status = isConnected ? "UNKNOWN" : "OFFLINE";
          }

          const isHealthy = status === "HEALTHY" || status === "NOMINAL";
          const isDegraded = status === "DEGRADED";

          return (
            <div
              key={sub.key}
              className="bg-space-850 border border-space-700/60 rounded p-2 flex flex-col gap-1 transition-colors"
            >
              <span className="text-slate-400 text-[9px] truncate">{sub.name.toUpperCase()}</span>
              <span
                className={`text-[11px] font-bold ${
                  isHealthy
                    ? "text-emerald-400"
                    : isDegraded
                    ? "text-amber-400"
                    : "text-rose-400"
                }`}
              >
                {status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
