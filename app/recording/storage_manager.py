"""Session recording storage catalog and manifest manager."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.paths import paths


class StorageManager:
    """Creates structured experiment session folders and writes metadata manifests."""

    def create_session_directory(self, experiment_id: str, run_id: str) -> Path:
        """Create date-partitioned session output directory."""
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        safe_exp = experiment_id.replace("/", "_").replace(" ", "_")
        session_dir = paths.recordings_dir / date_str / f"{safe_exp}_{run_id}"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def write_metadata(self, session_dir: Path, metadata: dict[str, Any]) -> Path:
        """Serialize metadata.json."""
        target = session_dir / "metadata.json"
        with target.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return target

    def write_events(self, session_dir: Path, events: list[dict[str, Any]]) -> Path:
        """Serialize events.json."""
        target = session_dir / "events.json"
        with target.open("w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
        return target

    def write_timeline_log(self, session_dir: Path, timeline: list[dict[str, Any]]) -> Path:
        """Serialize timeline.log."""
        target = session_dir / "timeline.log"
        with target.open("w", encoding="utf-8") as f:
            for item in timeline:
                ts = item.get("timestamp", "")
                etype = item.get("type", "")
                details = item.get("details", "")
                f.write(f"[{ts}] {etype:<24} - {details}\n")
        return target

    def list_recorded_sessions(self) -> list[dict[str, Any]]:
        """List all historical recorded experiment sessions."""
        sessions = []
        rec_dir = paths.recordings_dir
        if not rec_dir.is_dir():
            return []

        for meta_path in rec_dir.glob("*/*/metadata.json"):
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                video_file = meta_path.parent / "experiment.mp4"
                sessions.append({
                    "experiment_id": data.get("experiment_id", "UNKNOWN"),
                    "run_id": data.get("run_id", "UNKNOWN"),
                    "start_time": data.get("start_time", ""),
                    "duration_seconds": data.get("duration_seconds", 0),
                    "video_path": str(video_file) if video_file.is_file() else "",
                    "session_dir": str(meta_path.parent),
                })
            except Exception:
                pass

        return sorted(sessions, key=lambda x: x["start_time"], reverse=True)


storage_manager = StorageManager()
