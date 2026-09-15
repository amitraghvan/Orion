import { useEffect, useRef, useState } from "react";
import {
  EvidencePanel,
  ExperimentStatusPanel,
  MissionLogModal,
  NextStepGuidance,
  OpticalFeed,
  ProtocolViolationAlert,
  StepTimeline,
  SubsystemHealth,
  TelemetryLog,
  TopStatusBar,
  VoiceAlertSystem,
  type LogEntry,
} from "./components";
import { useTelemetry } from "./hooks/useTelemetry";
import { useTelemetryStore } from "./store/telemetryStore";

export default function App() {
  const {
    isConnected,
    subsystemStatuses,
    experimentStatus,
    lastDecision,
  } = useTelemetry();

  const [isLogModalOpen, setIsLogModalOpen] = useState<boolean>(false);
  const [eventLogs, setEventLogs] = useState<LogEntry[]>([]);
  const lastTrackActivitiesRef = useRef<Map<number, string>>(new Map());
  const lastRunIdRef = useRef<string>("");

  // Scope event log to active run
  useEffect(() => {
    const runId = experimentStatus?.run_id || "";
    if (runId && runId !== lastRunIdRef.current) {
      lastRunIdRef.current = runId;
      const now = new Date().toISOString().substring(11, 19);
      setEventLogs((prev) => [
        {
          time: now,
          text: `[EXPERIMENT ACTIVE] Run ID: ${runId} (FSM: ${experimentStatus?.fsm_state})`,
          type: "protocol",
        },
        ...prev,
      ].slice(0, 50));
      lastTrackActivitiesRef.current.clear();
    }
  }, [experimentStatus?.run_id, experimentStatus?.fsm_state]);

  // Append meaningful frame activity transitions to log stream (subscribes without re-rendering App at 30fps)
  useEffect(() => {
    const unsub = useTelemetryStore.subscribe((state) => {
      const frame = state.lastFrame;
      if (!frame || !frame.activities || frame.activities.length === 0) return;
      const now = new Date().toISOString().substring(11, 19);
      const newEvents: LogEntry[] = [];

      frame.activities.forEach((act) => {
        const p = act.top_prediction;
        const prevAct = lastTrackActivitiesRef.current.get(act.track_id);
        if (prevAct !== p.activity_name || p.phase === "START" || p.phase === "CHANGE") {
          lastTrackActivitiesRef.current.set(act.track_id, p.activity_name);
          newEvents.push({
            time: now,
            text: `[HAR Track #${act.track_id}] ${p.activity_name.toUpperCase()} (${(
              p.confidence * 100
            ).toFixed(1)}% | ${p.phase ?? "NOMINAL"})`,
            type: "activity",
          });
        }
      });

      if (newEvents.length > 0) {
        setEventLogs((prev) => [...newEvents, ...prev].slice(0, 50));
      }
    });

    return () => unsub();
  }, []);

  // Append protocol deviation events to log stream
  useEffect(() => {
    if (!lastDecision) return;
    const now = new Date().toISOString().substring(11, 19);
    const deviationType = lastDecision.status || lastDecision.deviation_type;
    if (["WRONG_OBJECT", "SKIPPED", "OUT_OF_SEQUENCE", "INTERRUPTED"].includes(deviationType)) {
      setEventLogs((prev) => [
        {
          time: now,
          text: `[PROTOCOL VIOLATION] ${deviationType}: ${
            lastDecision.explanation ||
            lastDecision.message ||
            "Out-of-sequence procedural deviation detected"
          }`,
          type: "protocol",
        },
        ...prev,
      ].slice(0, 50));
    }
  }, [lastDecision]);

  return (
    <div className="min-h-screen bg-space-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30">
      {/* Headless Voice Alert Synthesis System */}
      <VoiceAlertSystem />

      {/* Structured Mission Audit Log Modal */}
      <MissionLogModal
        isOpen={isLogModalOpen}
        onClose={() => setIsLogModalOpen(false)}
      />

      {/* Station Cockpit Top Bar */}
      <TopStatusBar onOpenLogModal={() => setIsLogModalOpen(true)} />

      {/* Main Cockpit Grid Layout */}
      <main className="flex-1 p-5 grid grid-cols-1 lg:grid-cols-12 gap-5 max-w-[1920px] mx-auto w-full">
        {/* Left Column: Optical Feed, Step Timeline & Telemetry Event Log (7 cols) */}
        <section className="lg:col-span-7 flex flex-col gap-5">
          <OpticalFeed isConnected={isConnected} />

          <StepTimeline />

          <TelemetryLog logs={eventLogs} />
        </section>

        {/* Right Column: Violation Alert, Guidance, Copilot, Evidence & Health (5 cols) */}
        <section className="lg:col-span-5 flex flex-col gap-5">
          {/* Active Protocol Violation (conditional banner with recovery options) */}
          <ProtocolViolationAlert />

          {/* Next Step Suggestion Guidance */}
          <NextStepGuidance />

          {/* Experiment Protocol Copilot & Controls */}
          <ExperimentStatusPanel />

          {/* Decision Evidence & Audit Rationale */}
          <EvidencePanel />

          {/* Station Subsystem Health */}
          <SubsystemHealth
            subsystemStatuses={subsystemStatuses}
            isConnected={isConnected}
          />
        </section>
      </main>

      {/* Cockpit Status Footer */}
      <footer className="border-t border-space-800 bg-space-900 px-6 py-2.5 flex flex-wrap items-center justify-between text-xs font-mono text-slate-400 gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span>ORION BAS AI COPILOT • SIH26174 • REAL BAS_REAL_DATA DATASET INTEGRATED</span>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-[11px]">
          <span>PIPELINE: 100% AIR-GAPPED</span>
          <span className="text-cyan-400">ST-GCN HAR: TRAINED & LOADED</span>
          <span className="text-emerald-400">HOI EVIDENCE ENGINE: ACTIVE</span>
          <span className="text-indigo-400">VOICE COPILOT: ONLINE</span>
          <span className="text-slate-500">EDGE RUNTIME: MPS / CPU</span>
        </div>
      </footer>
    </div>
  );
}
