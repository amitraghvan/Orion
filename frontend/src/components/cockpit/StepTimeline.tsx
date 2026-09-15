import React from "react";
import {
  CheckCircle2,
  Clock,
  Circle,
  ShieldAlert,
} from "lucide-react";
import { useTelemetryStore } from "../../store/telemetryStore";

export const StepTimeline: React.FC = () => {
  const experimentStatus = useTelemetryStore((state) => state.experimentStatus);
  const activeViolation = useTelemetryStore((state) => state.activeViolation);
  const fsmState = experimentStatus?.fsm_state ?? "LOADED";
  const currentStep = experimentStatus?.current_step;
  const currentStepNum = currentStep?.step_number ?? 1;

  const steps: any[] = (experimentStatus as any)?.specification?.steps ?? (experimentStatus?.steps as any[]) ?? [
    { step_number: 1, step_id: "S01", description: "Pick Yellow Box", expected_actions: ["pick_yellow"] },
    { step_number: 2, step_id: "S02", description: "Place Yellow Box", expected_actions: ["place_yellow"] },
    { step_number: 3, step_id: "S03", description: "Pick Red Box", expected_actions: ["pick_red"] },
    { step_number: 4, step_id: "S04", description: "Place Red Box", expected_actions: ["place_red"] },
  ];

  return (
    <div className="bg-space-900 border border-space-800 rounded-lg p-4 flex flex-col gap-3 shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold text-slate-100 tracking-wider uppercase">
            PROTOCOL STEP TIMELINE
          </h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
          <span>
            STEP {currentStepNum} OF {steps.length}
          </span>
          <span className="text-space-600">•</span>
          <span
            className={
              fsmState === "COMPLETED"
                ? "text-emerald-400 font-bold"
                : fsmState === "BLOCKED"
                ? "text-rose-400 font-bold"
                : "text-cyan-400 font-bold"
            }
          >
            {fsmState}
          </span>
        </div>
      </div>

      {/* Steps Horizontal Grid / Flow */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 pt-1">
        {steps.map((step: any, idx: number) => {
          const stepNum = step.step_number ?? idx + 1;
          const isCurrent = stepNum === currentStepNum && fsmState !== "COMPLETED";
          const isCompleted =
            stepNum < currentStepNum || fsmState === "COMPLETED";
          const isViolation = isCurrent && (activeViolation !== null || fsmState === "BLOCKED");

          let statusBadgeClass = "bg-space-800 text-slate-400 border-space-700";
          let statusText = "PENDING";
          let StatusIcon = Circle;

          if (isViolation) {
            statusBadgeClass = "bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-glow-rose/20";
            statusText = activeViolation?.type ?? "VIOLATION";
            StatusIcon = ShieldAlert;
          } else if (isCompleted) {
            statusBadgeClass = "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
            statusText = "COMPLETED";
            StatusIcon = CheckCircle2;
          } else if (isCurrent) {
            statusBadgeClass = "bg-cyan-500/20 text-cyan-300 border-cyan-400/50 animate-pulse shadow-glow-cyan/20";
            statusText = "IN PROGRESS";
            StatusIcon = Clock;
          }

          return (
            <div
              key={step.step_id || idx}
              className={`p-3 rounded border transition-all flex flex-col justify-between gap-2.5 ${
                isViolation
                  ? "bg-rose-950/30 border-rose-500/50"
                  : isCurrent
                  ? "bg-cyan-950/30 border-cyan-500/40"
                  : isCompleted
                  ? "bg-space-950/60 border-space-800"
                  : "bg-space-950/40 border-space-800/60 opacity-70"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-space-800 flex items-center justify-center text-[10px] font-mono font-bold text-slate-300">
                    {stepNum}
                  </span>
                  <span className="text-[11px] font-mono font-bold text-slate-300">
                    {step.step_id}
                  </span>
                </div>
                <div
                  className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wider border ${statusBadgeClass}`}
                >
                  <StatusIcon className="w-2.5 h-2.5" />
                  <span>{statusText}</span>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-slate-100 line-clamp-1" title={step.description}>
                  {step.description || `Step ${stepNum}`}
                </p>
                <div className="flex items-center gap-1 mt-1 text-[10px] font-mono text-cyan-400">
                  <span className="text-slate-500">ACTION:</span>
                  <span>{step.expected_actions?.[0]?.replace("_", " ") ?? "any"}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
