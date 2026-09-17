"""Integration test verifying end-to-end mission recording and structured reporting lifecycle."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from app.core.paths import paths
from app.experiments.experiment_engine import experiment_engine
from app.recording.recorder import experiment_recorder
from app.reports.report_generator import report_generator


def test_mission_recording_and_report_generation(tmp_path: Path):
    """Verify that starting and ending an experiment automatically produces MP4 and Markdown/JSON dossiers."""
    protocol_path = "configs/protocols/bas_e01_a.yaml"
    assert Path(protocol_path).exists()

    # 1. Load protocol
    spec = experiment_engine.load_protocol_file(protocol_path)
    assert spec is not None

    # 2. Start experiment
    run_id = experiment_engine.start_experiment()
    assert run_id.startswith("RUN-")
    assert experiment_recorder.is_recording is True

    # 3. Push synthetic frames at 30 FPS
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.putText(
        frame, "MISSION TEST FRAME", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2
    )
    for _ in range(15):
        experiment_recorder.push_frame(frame)

    # 4. Step 1: pick_yellow
    experiment_engine.process_observation("pick_yellow", confidence=0.92, entropy=0.2)
    experiment_engine.process_observation("pick_yellow", confidence=0.95, entropy=0.15)

    session_dir = experiment_recorder.session_dir
    assert session_dir is not None and session_dir.exists(), (
        f"Session dir not created at {session_dir}"
    )

    # 5. Stop/Finalize experiment
    experiment_engine.stop_experiment()
    assert experiment_recorder.is_recording is False

    # 6. Verify recording output artifacts

    video_file = session_dir / "experiment.mp4"
    assert video_file.exists(), f"Video file missing at {video_file}"
    assert video_file.stat().st_size > 0, "Video file has 0 bytes"

    # Verify playability via OpenCV
    cap = cv2.VideoCapture(str(video_file))
    assert cap.isOpened(), "Recorded MP4 could not be opened by OpenCV"
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    assert w == 1280
    assert h == 720
    cap.release()

    # Verify metadata and events
    meta_file = session_dir / "metadata.json"
    assert meta_file.exists()

    events_file = session_dir / "events.json"
    assert events_file.exists()

    timeline_file = session_dir / "timeline.log"
    assert timeline_file.exists()

    # 7. Verify structured mission report
    reports = list(paths.reports_dir.glob(f"REPORT_{spec.metadata.experiment_id}_{run_id}_*.md"))
    assert len(reports) >= 1, f"Markdown report not found in {paths.reports_dir}"
    md_content = reports[0].read_text(encoding="utf-8")
    assert spec.metadata.experiment_id in md_content
    assert run_id in md_content
    assert "Executive Procedural Summary" in md_content

    json_reports = list(
        paths.reports_dir.glob(f"REPORT_{spec.metadata.experiment_id}_{run_id}_*.json")
    )
    assert len(json_reports) >= 1, f"JSON report not found in {paths.reports_dir}"
    import json

    report_data = json.loads(json_reports[0].read_text(encoding="utf-8"))
    assert report_data["experiment_id"] == spec.metadata.experiment_id
    assert report_data["run_id"] == run_id
    assert len(report_data["steps"]) >= 1
