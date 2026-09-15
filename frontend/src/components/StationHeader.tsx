import React, { useEffect, useState } from "react";
import { Radio, Shield } from "lucide-react";

interface StationHeaderProps {
  isConnected: boolean;
  fps: number;
}

export const StationHeader: React.FC<StationHeaderProps> = ({ isConnected, fps }) => {
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toISOString().replace("T", " ").substring(0, 19) + " UTC");
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="border-b border-space-700 bg-space-900/90 backdrop-blur px-6 py-3 flex items-center justify-between sticky top-0 z-50 shadow-md">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-telemetry-400 animate-pulse" />
          <h1 className="text-base font-bold tracking-wider text-white">ORION BAS AI COPILOT</h1>
        </div>
        <span className="text-xs px-2.5 py-0.5 rounded bg-space-800 text-slate-300 font-mono border border-space-700">
          BAS-SCIENCE-NODE-1
        </span>
        <span className="text-xs px-2.5 py-0.5 rounded bg-telemetry-900 text-telemetry-400 font-mono border border-telemetry-600">
          GB-02 GLOVEBOX
        </span>
        <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 font-mono border border-cyan-700">
          PHASE 1.4: PROTOCOL INTELLIGENCE
        </span>
      </div>

      <div className="flex items-center gap-6">
        <div className="font-mono text-xs text-slate-400 flex items-center gap-2">
          <Radio className="w-3.5 h-3.5 text-telemetry-400" />
          {currentTime || "SYNCING UTC CLOCK..."}
        </div>

        <div className="flex items-center gap-2 px-3 py-1 rounded bg-space-850 border border-space-700">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isConnected ? "bg-nominal animate-pulse" : "bg-hazard"
            }`}
          />
          <span className="text-xs font-mono font-medium tracking-wide">
            {isConnected ? `LIVE TELEMETRY (${fps.toFixed(1)} FPS)` : "OFFLINE / DISCONNECTED"}
          </span>
        </div>
      </div>
    </header>
  );
};
