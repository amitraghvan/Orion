"""ORION Desktop Application main entrypoint."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Parse CLI options and launch desktop application."""
    parser = argparse.ArgumentParser(description="ORION: Offline AI BAS Experiment Assistant (SIH26174)")
    parser.add_argument("--demo", action="store_true", help="Launch in offline demonstration mode with sample video")
    parser.add_argument("--video", type=str, default=None, help="Override camera input with a specific video file")
    parser.add_argument("--camera", type=str, default=None, help="Camera device index (e.g. 0, 1) or stream URL")
    parser.add_argument("--protocol", type=str, default=None, help="Preload a specific experiment protocol YAML")
    args = parser.parse_args()

    # Lazy import to keep --help instantaneous
    from app.application import OrionApplication

    app = OrionApplication(
        demo_mode=args.demo,
        video_override=args.video,
        camera_source=args.camera,
        protocol_path=args.protocol,
    )
    sys.exit(app.run())


if __name__ == "__main__":
    main()
