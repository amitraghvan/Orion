"""Unit tests for ReportGenerator."""

import json
from pathlib import Path

from app.reports.report_generator import ReportGenerator


def test_generate_report(tmp_path: Path):
    gen = ReportGenerator()
    steps_log = [
        {
            "step_number": 1,
            "expected_action": "pick_yellow",
            "detected_action": "pick_yellow",
            "status": "VALID",
            "confidence": 0.92,
            "timestamp": "2026-09-16T12:00:00Z",
            "explanation": "Nominal execution",
        },
        {
            "step_number": 2,
            "expected_action": "place_yellow",
            "detected_action": "place_yellow",
            "status": "VALID",
            "confidence": 0.88,
            "timestamp": "2026-09-16T12:00:30Z",
            "explanation": "Nominal placement",
        },
    ]

    report_path = gen.generate_report(
        experiment_id="BAS_EXP_TEST",
        experiment_title="Test Titration Run",
        run_id="RUN_001",
        start_time="2026-09-16 12:00:00",
        end_time="2026-09-16 12:01:00",
        duration_seconds=60.0,
        steps_log=steps_log,
        system_info={"backend": "PyTorch / C++", "device": "CPU"},
        output_dir=tmp_path,
    )

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "ORION Mission Verification Report: BAS_EXP_TEST" in content
    assert "Test Titration Run" in content
    assert "RUN_001" in content
    assert "COMPLIANT" in content

    # Check companion JSON
    json_path = report_path.with_suffix(".json")
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["experiment_id"] == "BAS_EXP_TEST"
    assert data["completed_steps"] == 2
    assert data["skipped_steps"] == 0
    assert len(data["steps"]) == 2
