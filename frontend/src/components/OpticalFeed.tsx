import React, { useEffect, useRef, useState } from "react";
import {
  Activity,
  Camera,
  Eye,
  Layers,
  RefreshCw,
  Video,
  Zap,
  Play,
} from "lucide-react";
import { getAuthHeadersAsync } from "../services/auth";
import type { TelemetryFrame } from "../types/telemetry";
import { useTelemetryStore } from "../store/telemetryStore";

interface OpticalFeedProps {
  lastFrame?: TelemetryFrame | null;
  isConnected?: boolean;
  harLatency?: number;
}

interface ReplayOption {
  video_id: string;
  filename: string;
  path: string;
  is_valid: boolean;
  invalid_type: string | null;
  subject_id: string;
  experiment_id: string;
  variant: string;
  description: string;
  duration_seconds: number;
}

const COCO_BONES: Array<[number, number]> = [
  [15, 13], [13, 11], [16, 14], [14, 12], [11, 12],
  [5, 11], [6, 12], [5, 6], [5, 7], [6, 8],
  [7, 9], [8, 10], [1, 2], [0, 1], [0, 2],
  [1, 3], [2, 4], [3, 5], [4, 6],
];

export const OpticalFeed: React.FC<OpticalFeedProps> = ({
  lastFrame: propLastFrame,
  isConnected: propIsConnected,
  harLatency: propHarLatency,
}) => {
  const storeLastFrame = useTelemetryStore((state) => state.lastFrame);
  const storeIsConnected = useTelemetryStore((state) => state.isConnected);
  const lastFrame = propLastFrame !== undefined ? propLastFrame : storeLastFrame;
  const isConnected = propIsConnected !== undefined ? propIsConnected : storeIsConnected;
  const harLatency = propHarLatency ?? (lastFrame?.metrics?.har_latency_ms ?? 0);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamImgRef = useRef<HTMLImageElement | null>(null);

  // Overlay layer visibility toggles
  const [showFeed, setShowFeed] = useState<boolean>(true);
  const [showBoxes, setShowBoxes] = useState<boolean>(true);
  const [showSkeleton, setShowSkeleton] = useState<boolean>(true);
  const [showHands, setShowHands] = useState<boolean>(true);
  const [showObjects, setShowObjects] = useState<boolean>(true);
  const [showVectors, setShowVectors] = useState<boolean>(true);

  // Camera source & replays
  const [activeSource, setActiveSource] = useState<string>("0");
  const [cameraIndex, setCameraIndex] = useState<string>("0");
  const [isSwitchingSource, setIsSwitchingSource] = useState<boolean>(false);
  const [isCameraActive, setIsCameraActive] = useState<boolean>(true);
  const [, setStreamErrorCount] = useState<number>(0);
  const [isStreamBroken, setIsStreamBroken] = useState<boolean>(false);
  const [replays, setReplays] = useState<ReplayOption[]>([]);
  const [selectedReplay, setSelectedReplay] = useState<string>(
    "/Users/amitkumar/Downloads/BAS_REAL_DATA/VALID/SP04/AP01.mp4"
  );
  const [streamKey, setStreamKey] = useState<number>(Date.now());
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const setStreamingStatus = useTelemetryStore((state) => state.setStreamingStatus);
  const setStoreReplay = useTelemetryStore((state) => state.setSelectedReplay);
  const setCameraStatus = useTelemetryStore((state) => state.setCameraStatus);

  // Fetch available replays from backend
  useEffect(() => {
    const fetchReplays = async () => {
      try {
        const headers = await getAuthHeadersAsync();
        const res = await fetch("/api/v1/camera/replays", { headers });
        if (res.ok) {
          const data = await res.json();
          setReplays(data);
        }
      } catch (err) {
        console.error("Failed to fetch camera replays:", err);
      }
    };
    fetchReplays();
  }, []);

  // Handle switching camera source via backend API
  const handleSwitchSource = async (newSource: string) => {
    if (isSwitchingSource) return;
    setIsSwitchingSource(true);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/camera/source", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...headers },
        body: JSON.stringify({ source: newSource }),
      });
      if (res.ok) {
        setActiveSource(newSource);
        setStoreReplay(newSource === "0" || /^\d+$/.test(newSource) ? null : newSource);
        setStreamingStatus(newSource === "0" || /^\d+$/.test(newSource) ? "LOCAL" : "STREAMING");
        setIsStreamBroken(false);
        setStreamErrorCount(0);
        setIsCameraActive(true);
        setStreamKey(Date.now());
      }
    } catch (err) {
      console.error("Failed to switch camera source:", err);
    } finally {
      setIsSwitchingSource(false);
    }
  };

  // Explicit Start Camera Control
  const handleStartCamera = async () => {
    setIsSwitchingSource(true);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/camera/start", {
        method: "POST",
        headers,
      });
      if (res.ok) {
        setIsCameraActive(true);
        setIsStreamBroken(false);
        setStreamErrorCount(0);
        setStreamKey(Date.now());
        setCameraStatus({ connected: true, state: "CONNECTED" });
      }
    } catch (err) {
      console.error("Failed to start camera:", err);
    } finally {
      setIsSwitchingSource(false);
    }
  };

  // Explicit Stop Camera Control
  const handleStopCamera = async () => {
    setIsSwitchingSource(true);
    try {
      const headers = await getAuthHeadersAsync();
      const res = await fetch("/api/v1/camera/stop", {
        method: "POST",
        headers,
      });
      if (res.ok) {
        setIsCameraActive(false);
        setIsStreamBroken(true);
        setCameraStatus({ connected: false, state: "DISCONNECTED" });
      }
    } catch (err) {
      console.error("Failed to stop camera:", err);
    } finally {
      setIsSwitchingSource(false);
    }
  };

  // Controlled, throttled stream error handler to eliminate 500 error storms
  const handleStreamError = () => {
    setStreamErrorCount((prev) => {
      const next = prev + 1;
      if (next >= 3) {
        setIsStreamBroken(true);
      } else if (!retryTimerRef.current) {
        retryTimerRef.current = setTimeout(() => {
          retryTimerRef.current = null;
          if (streamImgRef.current && !isStreamBroken) {
            streamImgRef.current.src = `/api/v1/camera/frame?t=${Date.now()}`;
          }
        }, 1500);
      }
      return next;
    });
  };

  // Render transparent AI perception overlays onto canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const nativeWidth = lastFrame?.width || 640;
    const nativeHeight = lastFrame?.height || 480;
    if (canvas.width !== nativeWidth || canvas.height !== nativeHeight) {
      canvas.width = nativeWidth;
      canvas.height = nativeHeight;
    }

    const width = canvas.width;
    const height = canvas.height;

    // Clear previous overlay frame
    ctx.clearRect(0, 0, width, height);

    // 1. Draw Object Detections (Person & General Tools)
    if (showBoxes && lastFrame?.detections) {
      const ignored = new Set(["chair", "couch", "sofa", "bed", "dining table", "potted plant", "tv", "bench"]);
      lastFrame.detections.forEach((det) => {
        if (ignored.has(det.class_name.toLowerCase())) return;

        // If tracked hardware objects are rendered, avoid drawing duplicate raw box
        if (showObjects && lastFrame.objects && lastFrame.objects.length > 0) {
          const isHardware = det.class_name.includes("box") || det.class_name.includes("yellow") || det.class_name.includes("red");
          if (isHardware) return;
        }

        const { x_min, y_min, x_max, y_max } = det.box;
        const bw = x_max - x_min;
        const bh = y_max - y_min;

        const isYellow = det.class_name.includes("yellow");
        const isRed = det.class_name.includes("red");
        const color = isYellow ? "#facc15" : isRed ? "#f87171" : "#00e676";

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x_min, y_min, bw, bh);

        ctx.fillStyle = isYellow
          ? "rgba(250, 204, 21, 0.15)"
          : isRed
          ? "rgba(248, 113, 113, 0.15)"
          : "rgba(0, 230, 118, 0.12)";
        ctx.fillRect(x_min, y_min, bw, bh);

        const label = `${det.class_name.toUpperCase()} ${(det.confidence * 100).toFixed(0)}%`;
        ctx.font = "bold 10px 'JetBrains Mono', monospace";
        const textWidth = ctx.measureText(label).width;

        ctx.fillStyle = color;
        ctx.fillRect(x_min, Math.max(0, y_min - 16), textWidth + 8, 16);

        ctx.fillStyle = "#050811";
        ctx.fillText(label, x_min + 4, Math.max(12, y_min - 4));
      });
    }

    // 2. Draw Skeleton Keypoints and Bones
    if (showSkeleton && lastFrame?.poses) {
      lastFrame.poses.forEach((pose) => {
        const kpMap = new Map<number, { x: number; y: number; score: number }>();
        let avgX = 0;
        let minY = height;
        let validKpCount = 0;

        pose.keypoints_2d.forEach((kp) => {
          kpMap.set(kp.id, { x: kp.x, y: kp.y, score: kp.score });
          if (kp.score > 0.3) {
            avgX += kp.x;
            if (kp.y < minY) minY = kp.y;
            validKpCount++;
          }
        });

        // Draw Bones
        COCO_BONES.forEach(([j1, j2]) => {
          const p1 = kpMap.get(j1);
          const p2 = kpMap.get(j2);
          if (p1 && p2 && p1.score > 0.3 && p2.score > 0.3) {
            ctx.strokeStyle = "#00e5ff";
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        });

        // Draw Keypoint circles
        pose.keypoints_2d.forEach((kp) => {
          if (kp.score > 0.3) {
            ctx.fillStyle = "#00e5ff";
            ctx.beginPath();
            ctx.arc(kp.x, kp.y, 4, 0, Math.PI * 2);
            ctx.fill();

            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
        });

        // Pose Tag
        if (validKpCount > 4) {
          const labelX = avgX / validKpCount;
          const labelY = Math.max(16, minY - 10);
          ctx.font = "bold 11px 'JetBrains Mono', monospace";
          ctx.fillStyle = "#00e5ff";
          ctx.textAlign = "center";
          ctx.fillText(`SUBJECT [ID:${pose.person_id}]`, labelX, labelY);
        }
      });
    }

    // 3. Draw Hands
    if (showHands && lastFrame?.hands) {
      lastFrame.hands.forEach((hand) => {
        if (hand.region_bbox) {
          const { x_min, y_min, x_max, y_max } = hand.region_bbox;
          ctx.strokeStyle = "#f59e0b";
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4, 2]);
          ctx.strokeRect(x_min, y_min, x_max - x_min, y_max - y_min);
          ctx.setLineDash([]);

          ctx.font = "bold 9px 'JetBrains Mono', monospace";
          const tag = `${hand.side.toUpperCase()} [${hand.state.toUpperCase()}]`;
          ctx.fillStyle = "#f59e0b";
          ctx.textAlign = "left";
          ctx.fillText(tag, x_min + 2, Math.max(10, y_min - 3));
        }
      });
    }

    // 4. Draw Tracked Protocol Hardware Objects
    if (showObjects && lastFrame?.objects) {
      const deduplicated: typeof lastFrame.objects = [];
      lastFrame.objects.forEach((obj) => {
        const overlap = deduplicated.some((other) => {
          const xi1 = Math.max(obj.bbox.x_min, other.bbox.x_min);
          const yi1 = Math.max(obj.bbox.y_min, other.bbox.y_min);
          const xi2 = Math.min(obj.bbox.x_max, other.bbox.x_max);
          const yi2 = Math.min(obj.bbox.y_max, other.bbox.y_max);
          const inter = Math.max(0, xi2 - xi1) * Math.max(0, yi2 - yi1);
          const a1 = (obj.bbox.x_max - obj.bbox.x_min) * (obj.bbox.y_max - obj.bbox.y_min);
          const a2 = (other.bbox.x_max - other.bbox.x_min) * (other.bbox.y_max - other.bbox.y_min);
          const iou = inter / (a1 + a2 - inter + 1e-6);
          return iou > 0.35 && obj.class_name === other.class_name;
        });
        if (!overlap) {
          deduplicated.push(obj);
        }
      });

      deduplicated.forEach((obj) => {
        const { x_min, y_min, x_max, y_max } = obj.bbox;
        const bw = x_max - x_min;
        const bh = y_max - y_min;

        const isYellow = obj.class_name.includes("yellow");
        const isRed = obj.class_name.includes("red");
        const color = isYellow ? "#facc15" : isRed ? "#f87171" : "#38bdf8";

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x_min, y_min, bw, bh);

        ctx.fillStyle = isYellow
          ? "rgba(250, 204, 21, 0.15)"
          : isRed
          ? "rgba(248, 113, 113, 0.15)"
          : "rgba(56, 189, 248, 0.12)";
        ctx.fillRect(x_min, y_min, bw, bh);

        ctx.font = "bold 10px 'JetBrains Mono', monospace";
        const tag = `[OBJ] ${obj.class_name.toUpperCase()} ${(obj.confidence * 100).toFixed(0)}%`;
        const textWidth = ctx.measureText(tag).width;

        ctx.fillStyle = color;
        ctx.fillRect(x_min, Math.max(0, y_min - 16), textWidth + 8, 16);

        ctx.fillStyle = "#050811";
        ctx.textAlign = "left";
        ctx.fillText(tag, x_min + 4, Math.max(12, y_min - 4));
      });
    }

    // 5. Draw Hand-Object Interaction Vectors
    if (showVectors && lastFrame?.interactions && lastFrame?.hands && lastFrame?.objects) {
      lastFrame.interactions.forEach((intObs) => {
        if (intObs.state === "no_interaction") return;
        const h = lastFrame.hands?.find((hd) => hd.hand_id === intObs.hand_id);
        const o = lastFrame.objects?.find((ob) => ob.object_id === intObs.object_id);
        if (h?.region_bbox && o?.bbox) {
          const hx = (h.region_bbox.x_min + h.region_bbox.x_max) / 2;
          const hy = (h.region_bbox.y_min + h.region_bbox.y_max) / 2;
          const ox = (o.bbox.x_min + o.bbox.x_max) / 2;
          const oy = (o.bbox.y_min + o.bbox.y_max) / 2;

          const isEngaged =
            intObs.state === "grasping" ||
            intObs.state === "manipulating" ||
            intObs.state === "contact";
          ctx.strokeStyle = isEngaged ? "#10b981" : "#f59e0b";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(hx, hy);
          ctx.lineTo(ox, oy);
          ctx.stroke();

          const mx = (hx + ox) / 2;
          const my = (hy + oy) / 2;
          ctx.font = "bold 9px 'JetBrains Mono', monospace";
          const stLabel = intObs.state.toUpperCase();
          const w = ctx.measureText(stLabel).width;
          ctx.fillStyle = "#050811";
          ctx.fillRect(mx - w / 2 - 3, my - 7, w + 6, 14);
          ctx.fillStyle = isEngaged ? "#10b981" : "#f59e0b";
          ctx.textAlign = "center";
          ctx.fillText(stLabel, mx, my + 3);
        }
      });
    }
  }, [
    lastFrame,
    showBoxes,
    showSkeleton,
    showHands,
    showObjects,
    showVectors,
  ]);

  const frameIndex = lastFrame?.frame_index ?? 0;
  const detectionsCount = lastFrame?.detections?.length ?? 0;
  const posesCount = lastFrame?.poses?.length ?? 0;
  const activeActivities = lastFrame?.activities ?? [];

  const validReplays = replays.filter((r) => r.is_valid);
  const invalidReplays = replays.filter((r) => !r.is_valid);

  return (
    <div className="bg-space-900 border border-space-700 rounded-lg p-4 flex flex-col flex-1 shadow-lg">
      {/* Header with Title & Telemetry Indicators */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Camera className={`w-4 h-4 ${isConnected ? "text-cyan-400" : "text-rose-400"}`} />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            OPTICAL SENSOR FEED & AI SKELETON HAR OVERLAY
          </h2>
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? "bg-emerald-400 shadow-glow-emerald/30" : "bg-rose-500 animate-pulse"
            }`}
          />
        </div>
        <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
          <span>FRAME: #{frameIndex}</span>
          <span className="text-emerald-400">
            {lastFrame?.width ?? 640}x{lastFrame?.height ?? 480} RGB
          </span>
          <span className="text-cyan-400">HAR: {harLatency.toFixed(1)}ms</span>
        </div>
      </div>

      {/* Control Toolbar: Source Selector, Replay Dropdown, Camera Start/Stop, Layer Toggles */}
      <div className="flex flex-col gap-2 py-2 px-3 mb-2 rounded bg-space-850 border border-space-700 text-xs font-mono">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Source Controls */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-slate-400 flex items-center gap-1 text-[11px]">
              <Video className="w-3.5 h-3.5 text-cyan-400" /> SOURCE:
            </span>

            <div className="flex items-center gap-1">
              <button
                onClick={() => handleSwitchSource(cameraIndex)}
                disabled={isSwitchingSource}
                className={`px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
                  activeSource === cameraIndex
                    ? "bg-cyan-600 text-white shadow-glow-cyan/20"
                    : "bg-space-800 text-slate-400 hover:text-white"
                }`}
              >
                LIVE CAMERA (DEV {cameraIndex})
              </button>

              <select
                value={cameraIndex}
                onChange={(e) => {
                  setCameraIndex(e.target.value);
                  if (activeSource === "0" || /^\d+$/.test(activeSource)) {
                    handleSwitchSource(e.target.value);
                  }
                }}
                disabled={isSwitchingSource}
                className="bg-space-800 border border-space-700 text-slate-200 text-[11px] rounded px-1.5 py-1 focus:outline-none focus:border-cyan-500"
                title="Camera Device Index"
              >
                <option value="0">Index 0</option>
                <option value="1">Index 1</option>
                <option value="2">Index 2</option>
              </select>
            </div>

            {/* Real Camera Start / Stop Controls */}
            {isCameraActive ? (
              <button
                onClick={handleStopCamera}
                disabled={isSwitchingSource}
                className="px-2 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-[10px] font-bold tracking-wider transition flex items-center gap-1"
                title="Halt video capture and release hardware handle"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" /> STOP CAM
              </button>
            ) : (
              <button
                onClick={handleStartCamera}
                disabled={isSwitchingSource}
                className="px-2 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold tracking-wider transition flex items-center gap-1"
                title="Open video capture device"
              >
                <Play className="w-2.5 h-2.5" /> START CAM
              </button>
            )}

            {/* BAS Real Data Replay Dropdown */}
            <div className="flex items-center gap-1.5 pl-2 border-l border-space-700">
              <select
                value={selectedReplay}
                onChange={(e) => setSelectedReplay(e.target.value)}
                disabled={isSwitchingSource}
                className="bg-space-800 border border-space-700 text-slate-200 text-[11px] rounded px-2 py-1 max-w-[240px] truncate focus:outline-none focus:border-cyan-500"
              >
                <optgroup label="── BAS VALID PROTOCOL RUNS ──">
                  {validReplays.map((r) => (
                    <option key={r.video_id} value={r.path}>
                      {r.filename} — {r.experiment_id} Var {r.variant} ({r.subject_id})
                    </option>
                  ))}
                </optgroup>
                <optgroup label="── BAS INVALID / VIOLATION CLIPS ──">
                  {invalidReplays.map((r) => (
                    <option key={r.video_id} value={r.path}>
                      ⚠ {r.invalid_type}: {r.filename}
                    </option>
                  ))}
                </optgroup>
              </select>

              <button
                onClick={() => handleSwitchSource(selectedReplay)}
                disabled={isSwitchingSource}
                className={`flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-bold transition-colors ${
                  activeSource !== "0" && activeSource === selectedReplay
                    ? "bg-emerald-600 text-white shadow-glow-emerald/20"
                    : "bg-space-800 hover:bg-space-700 text-cyan-300 border border-cyan-500/30"
                }`}
              >
                <Play className="w-3 h-3" />
                PLAY REPLAY
              </button>
            </div>

            {isSwitchingSource && <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />}
          </div>

          {/* Active Source Badge */}
          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
                activeSource === "0" || /^\d+$/.test(activeSource)
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
              }`}
            >
              {activeSource === "0" || /^\d+$/.test(activeSource) ? "● LIVE FEED" : "▶ BAS EXPERIMENT REPLAY"}
            </span>
          </div>
        </div>

        {/* Overlay Layer Toggles */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-space-800 text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400 flex items-center gap-1 mr-1">
              <Layers className="w-3 h-3 text-slate-400" /> AI OVERLAYS:
            </span>
            <button
              onClick={() => setShowFeed(!showFeed)}
              className={`px-1.5 py-0.5 rounded ${
                showFeed ? "bg-cyan-950 text-cyan-300 border border-cyan-700" : "bg-space-800 text-slate-500"
              }`}
            >
              VIDEO
            </button>
            <button
              onClick={() => setShowBoxes(!showBoxes)}
              className={`px-1.5 py-0.5 rounded ${
                showBoxes ? "bg-emerald-950 text-emerald-300 border border-emerald-700" : "bg-space-800 text-slate-500"
              }`}
            >
              BOXES
            </button>
            <button
              onClick={() => setShowSkeleton(!showSkeleton)}
              className={`px-1.5 py-0.5 rounded ${
                showSkeleton ? "bg-cyan-950 text-cyan-300 border border-cyan-700" : "bg-space-800 text-slate-500"
              }`}
            >
              SKELETON
            </button>
            <button
              onClick={() => setShowHands(!showHands)}
              className={`px-1.5 py-0.5 rounded ${
                showHands ? "bg-amber-950 text-amber-300 border border-amber-700" : "bg-space-800 text-slate-500"
              }`}
            >
              HANDS
            </button>
            <button
              onClick={() => setShowObjects(!showObjects)}
              className={`px-1.5 py-0.5 rounded ${
                showObjects ? "bg-sky-950 text-sky-300 border border-sky-700" : "bg-space-800 text-slate-500"
              }`}
            >
              OBJECTS
            </button>
            <button
              onClick={() => setShowVectors(!showVectors)}
              className={`px-1.5 py-0.5 rounded ${
                showVectors ? "bg-emerald-950 text-emerald-300 border border-emerald-700" : "bg-space-800 text-slate-500"
              }`}
            >
              HOI VECTORS
            </button>
          </div>

          <span className="text-[10px] text-slate-500">
            {activeSource === "0" || /^\d+$/.test(activeSource) ? `Camera Index: ${activeSource}` : activeSource.split("/").pop()}
          </span>
        </div>
      </div>

      {/* Optical Viewport with Native Video & Transparent AI Canvas Overlay */}
      <div className="relative flex-1 min-h-[440px] bg-space-950 rounded border border-space-800 overflow-hidden flex items-center justify-center">
        {/* Background Grid if no feed */}
        <div className="absolute inset-0 bg-grid-pattern opacity-10 pointer-events-none" />

        {/* Live MJPEG Optical Video Stream or Disconnected State */}
        {showFeed ? (
          !isStreamBroken && isCameraActive ? (
            <img
              key={streamKey}
              ref={streamImgRef}
              src={`/api/v1/camera/stream?t=${streamKey}`}
              alt="Optical Video Stream"
              className="w-full h-full object-contain max-h-[520px]"
              onError={handleStreamError}
            />
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 p-6 text-center z-10">
              <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
                <Camera className="w-6 h-6" />
              </div>
              <div className="text-sm font-bold text-slate-200">CAMERA DISCONNECTED</div>
              <p className="text-xs text-slate-400 max-w-sm">
                Physical camera feed unavailable or optical capture halted.
              </p>
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={() => {
                    setIsCameraActive(true);
                    setIsStreamBroken(false);
                    setStreamErrorCount(0);
                    handleStartCamera();
                  }}
                  className="px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-lg shadow-cyan-600/20"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> RETRY CAMERA
                </button>
                <button
                  onClick={() => {
                    setIsCameraActive(true);
                    setIsStreamBroken(false);
                    setStreamErrorCount(0);
                    handleSwitchSource(selectedReplay);
                  }}
                  className="px-3 py-1.5 rounded bg-space-800 hover:bg-space-700 text-slate-200 text-xs font-bold transition border border-space-700 flex items-center gap-1.5"
                >
                  <Play className="w-3.5 h-3.5 text-emerald-400" /> USE REPLAY MODE
                </button>
              </div>
            </div>
          )
        ) : (
          <div className="w-full h-[480px] bg-space-950 flex items-center justify-center text-slate-600 font-mono text-xs">
            VIDEO STREAM MUTED
          </div>
        )}

        {/* Transparent Canvas Overlay for AI Perception (Bounding Boxes, Skeleton, Hands, HOI) */}
        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          className="absolute inset-0 w-full h-full object-contain max-h-[520px] pointer-events-none"
        />

        {/* Floating Telemetry Stats Badge */}
        <div className="absolute bottom-3 left-3 bg-space-900/90 backdrop-blur border border-space-700 rounded px-3 py-1.5 text-xs font-mono text-slate-300 flex items-center gap-3 shadow-lg">
          <span className="text-emerald-400 flex items-center gap-1">
            <Eye className="w-3.5 h-3.5" /> {detectionsCount} Targets
          </span>
          <span className="text-cyan-400 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5" /> {posesCount} Poses
          </span>
          <span className="text-amber-400 flex items-center gap-1">
            <Zap className="w-3.5 h-3.5" /> {activeActivities.length} Actions
          </span>
        </div>
      </div>

      {/* Authoritative Optical Feed Telemetry Panel (Section 16 requirement) */}
      <div className="mt-2 px-3 py-1.5 rounded bg-space-900 border border-space-800 flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-4">
          <span>
            SOURCE: <strong className="text-slate-200">{activeSource === "0" || /^\d+$/.test(activeSource) ? "LIVE CAMERA" : "REPLAY VIDEO"}</strong>
          </span>
          <span>
            CAMERA: <strong className="text-cyan-400">{activeSource === "0" || /^\d+$/.test(activeSource) ? activeSource : "FILE"}</strong>
          </span>
          <span>
            STATUS:{" "}
            <strong className={isCameraActive && !isStreamBroken ? "text-emerald-400" : "text-rose-400"}>
              {isCameraActive && !isStreamBroken ? "CONNECTED" : "DISCONNECTED"}
            </strong>
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span>
            FPS: <strong className="text-emerald-400">{lastFrame?.metrics?.fps ? lastFrame.metrics.fps.toFixed(1) : (isCameraActive && !isStreamBroken ? "30.0" : "0.0")}</strong>
          </span>
          <span>
            FRAME: <strong className="text-slate-200">#{frameIndex}</strong>
          </span>
        </div>
      </div>
    </div>
  );
};
