"""Generate canonical protocol YAMLs for all 5 BAS experiments and variants."""

import yaml
from pathlib import Path

BASE_METADATA = {
    "lead_agency": "ISRO HSFC",
    "station_module": "BAS-SCIENCE-NODE-1",
    "glovebox_id": "GB-01",
    "principal_investigator": "Astronaut Scientist / HSFC Payload Specialist",
    "date_approved": "2026-09-14",
    "safety_classification": "LEVEL-1-NON-HAZARDOUS",
}

OBJECTS_BASE = [
    {
        "object_id": "yellow_box",
        "label": "yellow_box",
        "required": True,
        "expected_detection_model": "bas-det-yolo11-v1",
        "min_confidence": 0.70,
    },
    {
        "object_id": "red_box",
        "label": "red_box",
        "required": True,
        "expected_detection_model": "bas-det-yolo11-v1",
        "min_confidence": 0.70,
    },
]

EXPERIMENTS_DEF = {
    "E01_A": {
        "id": "BAS-EXP-E01-A",
        "title": "E01 Detecting Colour (Variant A: Yellow then Red)",
        "objects": OBJECTS_BASE,
        "steps": [
            {
                "step_id": "E01_A_S01",
                "step_number": 1,
                "description": "Pick up yellow box and place it back in its respective place.",
                "expected_activity": "pick_yellow",
                "expected_actions": ["pick_yellow", "pick"],
                "allowed_transitions": ["E01_A_S02"],
            },
            {
                "step_id": "E01_A_S02",
                "step_number": 2,
                "description": "Place yellow box back in its respective place.",
                "expected_activity": "place_yellow",
                "expected_actions": ["place_yellow", "place"],
                "allowed_transitions": ["E01_A_S03"],
            },
            {
                "step_id": "E01_A_S03",
                "step_number": 3,
                "description": "Pick up red box and place it back in its respective place.",
                "expected_activity": "pick_red",
                "expected_actions": ["pick_red", "pick"],
                "allowed_transitions": ["E01_A_S04"],
            },
            {
                "step_id": "E01_A_S04",
                "step_number": 4,
                "description": "Place red box back in its respective place.",
                "expected_activity": "place_red",
                "expected_actions": ["place_red", "place"],
                "allowed_transitions": [],
            },
        ],
    },
    "E01_B": {
        "id": "BAS-EXP-E01-B",
        "title": "E01 Detecting Colour (Variant B: Red then Yellow)",
        "objects": OBJECTS_BASE,
        "steps": [
            {
                "step_id": "E01_B_S01",
                "step_number": 1,
                "description": "Pick up red box and place it back in its respective place.",
                "expected_activity": "pick_red",
                "expected_actions": ["pick_red", "pick"],
                "allowed_transitions": ["E01_B_S02"],
            },
            {
                "step_id": "E01_B_S02",
                "step_number": 2,
                "description": "Place red box back in its respective place.",
                "expected_activity": "place_red",
                "expected_actions": ["place_red", "place"],
                "allowed_transitions": ["E01_B_S03"],
            },
            {
                "step_id": "E01_B_S03",
                "step_number": 3,
                "description": "Pick up yellow box and place it back in its respective place.",
                "expected_activity": "pick_yellow",
                "expected_actions": ["pick_yellow", "pick"],
                "allowed_transitions": ["E01_B_S04"],
            },
            {
                "step_id": "E01_B_S04",
                "step_number": 4,
                "description": "Place yellow box back in its respective place.",
                "expected_activity": "place_yellow",
                "expected_actions": ["place_yellow", "place"],
                "allowed_transitions": [],
            },
        ],
    },
    "E02_A": {
        "id": "BAS-EXP-E02-A",
        "title": "E02 Interchanging the Boxes (Variant A)",
        "objects": OBJECTS_BASE,
        "steps": [
            {
                "step_id": "E02_A_S01",
                "step_number": 1,
                "description": "Pick up both boxes.",
                "expected_activity": "pick_both",
                "expected_actions": ["pick_both", "pick"],
                "allowed_transitions": ["E02_A_S02"],
            },
            {
                "step_id": "E02_A_S02",
                "step_number": 2,
                "description": "Put the yellow box on the red box's place.",
                "expected_activity": "place_yellow",
                "expected_actions": ["place_yellow", "place"],
                "allowed_transitions": ["E02_A_S03"],
            },
            {
                "step_id": "E02_A_S03",
                "step_number": 3,
                "description": "Put the red box on the yellow box's place.",
                "expected_activity": "place_red",
                "expected_actions": ["place_red", "place"],
                "allowed_transitions": [],
            },
        ],
    },
    "E02_B": {
        "id": "BAS-EXP-E02-B",
        "title": "E02 Interchanging the Boxes (Variant B)",
        "objects": OBJECTS_BASE,
        "steps": [
            {
                "step_id": "E02_B_S01",
                "step_number": 1,
                "description": "Pick up both boxes.",
                "expected_activity": "pick_both",
                "expected_actions": ["pick_both", "pick"],
                "allowed_transitions": ["E02_B_S02"],
            },
            {
                "step_id": "E02_B_S02",
                "step_number": 2,
                "description": "Put the red box on the yellow box's place.",
                "expected_activity": "place_red",
                "expected_actions": ["place_red", "place"],
                "allowed_transitions": ["E02_B_S03"],
            },
            {
                "step_id": "E02_B_S03",
                "step_number": 3,
                "description": "Put the yellow box on the red box's place.",
                "expected_activity": "place_yellow",
                "expected_actions": ["place_yellow", "place"],
                "allowed_transitions": [],
            },
        ],
    },
    "E03_A": {
        "id": "BAS-EXP-E03-A",
        "title": "E03 Overlapping the Boxes (Variant A)",
        "objects": OBJECTS_BASE,
        "steps": [
            {
                "step_id": "E03_A_S01",
                "step_number": 1,
                "description": "Place two boxes — red and yellow.",
                "expected_activity": "place_both",
                "expected_actions": ["place_both", "place"],
                "allowed_transitions": ["E03_A_S02"],
            },
            {
                "step_id": "E03_A_S02",
                "step_number": 2,
                "description": "Put the yellow box on the red box.",
                "expected_activity": "overlap_yellow_on_red",
                "expected_actions": ["overlap_yellow_on_red", "overlap", "place"],
                "allowed_transitions": [],
            },
        ],
    },
    "E03_B": {
        "id": "BAS-EXP-E03-B",
        "title": "E03 Overlapping the Boxes (Variant B)",
        "objects": OBJECTS_BASE,
        "steps": [
            {
                "step_id": "E03_B_S01",
                "step_number": 1,
                "description": "Place two boxes — red and yellow.",
                "expected_activity": "place_both",
                "expected_actions": ["place_both", "place"],
                "allowed_transitions": ["E03_B_S02"],
            },
            {
                "step_id": "E03_B_S02",
                "step_number": 2,
                "description": "Put the red box on the yellow box.",
                "expected_activity": "overlap_red_on_yellow",
                "expected_actions": ["overlap_red_on_yellow", "overlap", "place"],
                "allowed_transitions": [],
            },
        ],
    },
    "E04_A": {
        "id": "BAS-EXP-E04-A",
        "title": "E04 Moving (Variant A)",
        "objects": OBJECTS_BASE,
        "steps": [
            {
                "step_id": "E04_A_S01",
                "step_number": 1,
                "description": "Keep the yellow box in its respective place.",
                "expected_activity": "place_yellow",
                "expected_actions": ["place_yellow", "place", "idle"],
                "allowed_transitions": ["E04_A_S02"],
            },
            {
                "step_id": "E04_A_S02",
                "step_number": 2,
                "description": "Move the red box towards the yellow box.",
                "expected_activity": "move_red_to_yellow",
                "expected_actions": ["move_red_to_yellow", "move"],
                "allowed_transitions": [],
            },
        ],
    },
    "E04_B": {
        "id": "BAS-EXP-E04-B",
        "title": "E04 Moving (Variant B)",
        "objects": OBJECTS_BASE,
        "steps": [
            {
                "step_id": "E04_B_S01",
                "step_number": 1,
                "description": "Keep the red box in its respective place.",
                "expected_activity": "place_red",
                "expected_actions": ["place_red", "place", "idle"],
                "allowed_transitions": ["E04_B_S02"],
            },
            {
                "step_id": "E04_B_S02",
                "step_number": 2,
                "description": "Move the yellow box towards the red box.",
                "expected_activity": "move_yellow_to_red",
                "expected_actions": ["move_yellow_to_red", "move"],
                "allowed_transitions": [],
            },
        ],
    },
    "E05_A": {
        "id": "BAS-EXP-E05-A",
        "title": "E05 In Container (Variant A)",
        "objects": OBJECTS_BASE + [{
            "object_id": "container",
            "label": "container",
            "required": True,
            "expected_detection_model": "bas-det-yolo11-v1",
            "min_confidence": 0.65,
        }],
        "steps": [
            {
                "step_id": "E05_A_S01",
                "step_number": 1,
                "description": "Pick yellow box from container.",
                "expected_activity": "pick_yellow",
                "expected_actions": ["pick_yellow", "pick"],
                "allowed_transitions": ["E05_A_S02"],
            },
            {
                "step_id": "E05_A_S02",
                "step_number": 2,
                "description": "Check it.",
                "expected_activity": "check_yellow",
                "expected_actions": ["check_yellow", "check", "inspect"],
                "allowed_transitions": ["E05_A_S03"],
            },
            {
                "step_id": "E05_A_S03",
                "step_number": 3,
                "description": "Pick red box from container.",
                "expected_activity": "pick_red",
                "expected_actions": ["pick_red", "pick"],
                "allowed_transitions": ["E05_A_S04"],
            },
            {
                "step_id": "E05_A_S04",
                "step_number": 4,
                "description": "Check it.",
                "expected_activity": "check_red",
                "expected_actions": ["check_red", "check", "inspect"],
                "allowed_transitions": [],
            },
        ],
    },
    "E05_B": {
        "id": "BAS-EXP-E05-B",
        "title": "E05 In Container (Variant B)",
        "objects": OBJECTS_BASE + [{
            "object_id": "container",
            "label": "container",
            "required": True,
            "expected_detection_model": "bas-det-yolo11-v1",
            "min_confidence": 0.65,
        }],
        "steps": [
            {
                "step_id": "E05_B_S01",
                "step_number": 1,
                "description": "Pick red box from container.",
                "expected_activity": "pick_red",
                "expected_actions": ["pick_red", "pick"],
                "allowed_transitions": ["E05_B_S02"],
            },
            {
                "step_id": "E05_B_S02",
                "step_number": 2,
                "description": "Check it.",
                "expected_activity": "check_red",
                "expected_actions": ["check_red", "check", "inspect"],
                "allowed_transitions": ["E05_B_S03"],
            },
            {
                "step_id": "E05_B_S03",
                "step_number": 3,
                "description": "Pick yellow box from container.",
                "expected_activity": "pick_yellow",
                "expected_actions": ["pick_yellow", "pick"],
                "allowed_transitions": ["E05_B_S04"],
            },
            {
                "step_id": "E05_B_S04",
                "step_number": 4,
                "description": "Check it.",
                "expected_activity": "check_yellow",
                "expected_actions": ["check_yellow", "check", "inspect"],
                "allowed_transitions": [],
            },
        ],
    },
}

def generate_yaml(code: str, data: dict) -> dict:
    steps = []
    for s in data["steps"]:
        steps.append({
            "step_id": s["step_id"],
            "step_number": s["step_number"],
            "step_order": s["step_number"],
            "description": s["description"],
            "expected_activity": s["expected_activity"],
            "expected_actions": s["expected_actions"],
            "optional": False,
            "allowed_transitions": s["allowed_transitions"],
            "timeouts": {
                "nominal_duration_seconds": 30,
                "max_timeout_seconds": 90,
            },
            "thresholds": {
                "activity_confidence_min": 0.65,
                "pose_tracking_stability_min": 0.75,
                "interaction_proximity_px": 100.0,
            },
            "validation_rules": [
                {
                    "rule_id": f"RULE-{s['step_id']}",
                    "predicate": "interaction_active == true",
                    "severity": "WARNING",
                }
            ],
        })

    spec = {
        "schema_version": "1.0.0",
        "metadata": {
            "experiment_id": data["id"],
            "title": data["title"],
            **BASE_METADATA,
        },
        "objects": data["objects"],
        "steps": steps,
        "alerts": [
            {
                "alert_id": "ALERT-WRONG-OBJECT",
                "trigger": "wrong_object_detected",
                "severity": "WARNING",
                "spoken_message": "Warning. Expected object operation mismatch.",
            },
            {
                "alert_id": "ALERT-STEP-SKIPPED",
                "trigger": "step_skipped",
                "severity": "WARNING",
                "spoken_message": "Step skipped. Please perform the required step.",
            },
            {
                "alert_id": "ALERT-OUT-OF-SEQUENCE",
                "trigger": "out_of_sequence",
                "severity": "WARNING",
                "spoken_message": "Experiment sequence violation detected.",
            },
        ],
        "recovery": {
            "on_timeout": {"action": "RETRY_STEP"},
            "on_tool_lost": {"action": "PAUSE_EXPERIMENT"},
        },
    }
    return spec

def main():
    target_dir = Path("configs/protocols")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    index = {}
    for code, data in EXPERIMENTS_DEF.items():
        spec = generate_yaml(code, data)
        filename = f"bas_{code.lower()}.yaml"
        file_path = target_dir / filename
        with open(file_path, "w") as f:
            yaml.dump(spec, f, sort_keys=False, indent=2)
        print(f"Generated: {file_path}")
        index[code] = {
            "experiment_id": data["id"],
            "title": data["title"],
            "file": str(file_path),
            "step_count": len(spec["steps"]),
        }
    
    # Save canonical bas_experiments_index.json
    import json
    with open(target_dir / "experiments_index.json", "w") as f:
        json.dump(index, f, indent=2)
    print("Generated: configs/protocols/experiments_index.json")

if __name__ == "__main__":
    main()
