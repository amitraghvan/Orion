"""CLI Replay Harness for testing ORION Protocol Engine against scripted HAR activity streams."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from experiments.loader import load_protocol

from orion.events.schemas import ActivityRecognized
from orion.protocol.service import ProtocolService


def run_scenario(scenario_name: str, protocol_path: str) -> bool:
    """Run an automated scenario replay."""
    print("\n========================================================")
    print(f" ORION BAS AI COPILOT — PROTOCOL REPLAY: {scenario_name}")
    print(f" Protocol: {protocol_path}")
    print("========================================================\n")

    spec = load_protocol(protocol_path)
    h_str = spec.protocol_hash[:16] if spec.protocol_hash else "UNKNOWN"
    print(f"✓ Protocol verified: {spec.metadata.experiment_id} (SHA-256: {h_str}...)")
    print(f"✓ Steps loaded: {len(spec.steps)}")

    service = ProtocolService()
    service.load_protocol_file(protocol_path)
    run_id = service.start_experiment()
    print(f"✓ Run started: {run_id} | Initial State: {service.state.value}\n")

    # Define test streams for scenarios
    events: list[dict[str, Any]] = []

    if scenario_name == "nominal":
        # 2 events of each of the 6 steps with confidence 0.90
        actions = ["prepare_workstation", "reach_tool", "grasp_tool", "manipulate_sample", "inspect_chamber", "idle"]
        for act in actions:
            for _ in range(2):
                events.append({"activity": act, "confidence": 0.92, "entropy": 0.35})

    elif scenario_name == "out_of_sequence":
        # Step 1 valid, then premature step 4
        events.append({"activity": "prepare_workstation", "confidence": 0.90, "entropy": 0.30})
        events.append({"activity": "prepare_workstation", "confidence": 0.90, "entropy": 0.30})
        # Premature manipulate_sample
        events.append({"activity": "manipulate_sample", "confidence": 0.88, "entropy": 0.40})
        events.append({"activity": "manipulate_sample", "confidence": 0.88, "entropy": 0.40})

    elif scenario_name == "high_entropy":
        # Step 1, then high entropy event
        events.append({"activity": "prepare_workstation", "confidence": 0.90, "entropy": 0.30})
        events.append({"activity": "prepare_workstation", "confidence": 0.90, "entropy": 1.75})  # > 1.40 threshold

    elif scenario_name == "unknown_action":
        events.append({"activity": "floating_pen", "confidence": 0.85, "entropy": 0.50})
        events.append({"activity": "unknown", "confidence": 0.50, "entropy": 0.50})

    else:
        print(f"Unknown scenario: {scenario_name}")
        return False

    # Execute events
    import asyncio

    async def _replay() -> bool:
        for i, item in enumerate(events):
            act_label = item["activity"]
            conf = item["confidence"]
            ent = item["entropy"]

            event = ActivityRecognized(
                track_id=1,
                window_start_frame=i * 32,
                window_end_frame=(i + 1) * 32,
                activity_label=act_label,
                confidence=conf,
                uncertainty_status="NOMINAL" if ent < 1.40 and conf >= 0.70 else "UNCERTAIN",
                evidence_metadata={
                    "entropy": ent,
                    "probabilities": {act_label: conf},
                },
            )

            decision = await service.process_activity(event)
            status_str = decision.status.value if decision else "IGNORED"
            step_str = service.fsm.current_step.step_id if service.fsm.current_step else "COMPLETED"
            rec = service._last_recommendation

            print(f"[{i+1:02d}] Observed: {act_label:<20} | Conf: {conf:.2f} | H: {ent:.2f} "
                  f"-> Decision: {status_str:<20} | FSM: {service.state.value:<16} | Step: {step_str}")
            if rec:
                print(f"     Guidance: {rec.instruction_text} ({rec.expected_activity})")

        print(f"\nFinal State: {service.state.value}")
        return True

    return asyncio.run(_replay())


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION BAS Protocol Scenario Replay")
    parser.add_argument(
        "--scenario",
        default="nominal",
        choices=["nominal", "out_of_sequence", "high_entropy", "unknown_action"],
        help="Test scenario to execute",
    )
    parser.add_argument(
        "--protocol",
        default="configs/protocols/bas_crystal_growth_v1.yaml",
        help="Path to protocol YAML",
    )
    args = parser.parse_args()
    success = run_scenario(args.scenario, args.protocol)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
