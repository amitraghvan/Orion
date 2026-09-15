import React from "react";
import { ArrowRight, Compass, ShieldCheck } from "lucide-react";
import { useTelemetryStore } from "../../store/telemetryStore";

export const NextStepGuidance: React.FC = () => {
  const experimentStatus = useTelemetryStore((state) => state.experimentStatus);
  const fsmState = experimentStatus?.fsm_state ?? "LOADED";
  const currentStep = experimentStatus?.current_step;
  const currentStepNum = currentStep?.step_number ?? 1;
  const steps: any[] = (experimentStatus as any)?.specification?.steps ?? (experimentStatus?.steps as any[]) ?? [];

  // Determine next step
  const nextStep = steps.find((s: any) => (s.step_number ?? 0) === currentStepNum + 1);

  if (fsmState === "COMPLETED") {
    return (
      <div className="bg-emerald-950/40 border border-emerald-500/40 rounded-lg p-5 flex flex-col gap-2 shadow-glow-emerald">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <h3 className="text-xs font-bold text-emerald-300 tracking-wider uppercase">
            EXPERIMENT COMPLETED SUCCESSFULLY
          </h3>
        </div>
        <p className="text-xs text-slate-200">
          All protocol steps have been validated according to the mission specification. 0 sequence violations detected.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-cyan-950/40 to-space-900 border border-cyan-500/30 rounded-lg p-5 flex flex-col gap-3 shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4 text-cyan-400" />
          <span className="text-[10px] font-bold text-cyan-300 tracking-widest uppercase">
            NEXT STEP SUGGESTION (SIH CO-PILOT)
          </span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
          GUIDANCE ACTIVE
        </span>
      </div>

      <div className="flex items-center gap-3 bg-space-950/80 border border-space-800 rounded p-4">
        <div className="w-10 h-10 rounded-full bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-400 font-bold shrink-0">
          <ArrowRight className="w-5 h-5" />
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
            STEP {nextStep ? (nextStep.step_number ?? currentStepNum + 1) : currentStepNum}:
          </span>
          <h4 className="text-sm font-bold text-slate-100">
            {nextStep
              ? nextStep.description || nextStep.step_id
              : currentStep?.description || "Execute active step procedure"}
          </h4>
          <span className="text-[11px] text-cyan-300 font-medium">
            Expected Action: {nextStep ? (nextStep.expected_actions?.[0] || "execute").replace("_", " ") : "awaiting execution"}
          </span>
        </div>
      </div>
    </div>
  );
};
