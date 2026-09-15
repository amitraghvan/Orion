import React, { useEffect, useState } from "react";
import {
  Activity,
  Camera,
  Cpu,
  FileCode,
  HardDrive,
  Radio,
  Volume2,
} from "lucide-react";
import { useTelemetryStore } from "../../store/telemetryStore";

interface TopStatusBarProps {
  onOpenLogModal?: () => void;
}

export const TopStatusBar: React.FC<TopStatusBarProps> = ({ onOpenLogModal }) => {
  const cameraStatus = useTelemetryStore((state) => state.cameraStatus);
  const aiStatus = useTelemetryStore((state) => state.aiStatus);
  const voiceStatus = useTelemetryStore((state) => state.voiceStatus);
  const recordingStatus = useTelemetryStore((state) => state.recordingStatus);
  const streamingStatus = useTelemetryStore((state) => state.streamingStatus);
  const modelInfo = useTelemetryStore((state) => state.modelInfo);
  const fps = useTelemetryStore((state) => state.cameraStatus.fps || state.lastFrame?.metrics?.fps || 0);

  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toISOString().substring(11, 19) + " UTC");
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-space-900 border-b border-space-800 px-6 py-3 flex flex-wrap items-center justify-between gap-4 select-none">
      {/* Title & Mission */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-400 font-black tracking-wider shadow-glow-cyan">
            O
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold tracking-widest text-slate-100 uppercase">
                ORION BAS AI COPILOT
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 tracking-wider">
                OFFLINE / EDGE
              </span>
            </div>
            <p className="text-[11px] text-slate-400 tracking-wider">
              MISSION: SIH26174 — ON-BOARD BAS EXPERIMENTS
            </p>
          </div>
        </div>

        {/* AI Model & Dataset badges */}
        <div className="hidden xl:flex items-center gap-2 pl-4 border-l border-space-800 text-[11px]">
          <div className="px-2 py-0.5 rounded bg-space-800 text-cyan-400 border border-cyan-500/30 flex items-center gap-1 font-mono">
            <Cpu className="w-3 h-3 text-cyan-400" />
            <span>MODEL: {modelInfo.modelId}</span>
          </div>
          <div className="px-2 py-0.5 rounded bg-space-800 text-indigo-300 border border-indigo-500/30 flex items-center gap-1 font-mono">
            <HardDrive className="w-3 h-3 text-indigo-400" />
            <span>DATA: {modelInfo.datasetVersion}</span>
          </div>
        </div>
      </div>

      {/* Subsystem Telemetry Status Indicators */}
      <div className="flex items-center gap-3 text-xs">
        {/* Optical Camera */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-space-800 border border-space-700">
          <Camera className={`w-3.5 h-3.5 ${cameraStatus.connected ? "text-cyan-400" : "text-slate-500"}`} />
          <span className="text-[11px] font-medium text-slate-300">CAM:</span>
          <span className={`text-[11px] font-bold ${
            cameraStatus.connected
              ? "text-emerald-400"
              : cameraStatus.state === "CONNECTING"
              ? "text-amber-400"
              : "text-rose-400"
          }`}>
            {cameraStatus.connected ? (cameraStatus.state === "STREAMING" ? "CONNECTED" : "CONNECTED") : "DISCONNECTED"}
          </span>
          <span className="text-[10px] text-slate-500 font-mono pl-1">
            {cameraStatus.connected && fps > 0 ? `${fps.toFixed(1)} FPS` : "-- FPS"}
          </span>
        </div>

        {/* AI Perception Engine */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-space-800 border border-space-700">
          <Activity className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-[11px] font-medium text-slate-300">AI:</span>
          <span className={`text-[11px] font-bold ${
            !cameraStatus.connected
              ? "text-slate-400"
              : aiStatus === "PROCESSING"
              ? "text-cyan-400"
              : aiStatus === "READY"
              ? "text-emerald-400"
              : aiStatus === "DEGRADED"
              ? "text-amber-400"
              : "text-rose-400"
          }`}>
            {!cameraStatus.connected ? "WAITING FOR CAMERA" : aiStatus}
          </span>
        </div>

        {/* Voice System */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-space-800 border border-space-700">
          <Volume2 className={`w-3.5 h-3.5 ${voiceStatus === "ALERT_ACTIVE" ? "text-amber-400 animate-pulse" : "text-slate-400"}`} />
          <span className="text-[11px] font-medium text-slate-300">VOICE:</span>
          <span className={`text-[11px] font-bold ${voiceStatus === "ALERT_ACTIVE" ? "text-amber-400" : "text-emerald-400"}`}>
            {voiceStatus}
          </span>
        </div>

        {/* Recording Status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-space-800 border border-space-700">
          <span className={`w-2 h-2 rounded-full ${recordingStatus === "RECORDING" ? "bg-rose-500 animate-ping" : "bg-slate-500"}`} />
          <span className="text-[11px] font-medium text-slate-300">REC:</span>
          <span className={`text-[11px] font-bold ${recordingStatus === "RECORDING" ? "text-rose-400" : "text-slate-400"}`}>
            {recordingStatus}
          </span>
        </div>

        {/* Stream Status */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-space-800 border border-space-700">
          <Radio className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px] font-medium text-slate-300">STREAM:</span>
          <span className="text-[11px] font-bold text-cyan-400">
            {streamingStatus}
          </span>
        </div>

        {/* Clock */}
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded bg-space-950 border border-space-800 font-mono text-[12px] text-cyan-300 font-semibold shadow-inner">
          <span>{timeStr}</span>
        </div>

        {/* Audit Log Modal Trigger */}
        {onOpenLogModal && (
          <button
            onClick={onOpenLogModal}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300 border border-cyan-500/40 font-mono text-[11px] font-bold transition shadow-sm"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>AUDIT LOG</span>
          </button>
        )}
      </div>
    </header>
  );
};
