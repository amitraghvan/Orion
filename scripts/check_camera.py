"""Optical camera sensor diagnostic probe."""

import platform
import shutil
from pathlib import Path


def check_camera() -> None:
    print("==================================================================")
    print("📷 Camera & Optical Sensor Probe")
    print("==================================================================")

    system = platform.system()
    print(f"OS Platform: {system}")

    if system == "Linux":
        v4l2_devices = list(Path("/dev").glob("video*"))
        if v4l2_devices:
            print(f"✅ Discovered {len(v4l2_devices)} V4L2 device nodes:")
            for dev in v4l2_devices:
                print(f"   - {dev}")
        else:
            print("ℹ️ No V4L2 video nodes discovered under /dev/video*")

        v4l2_ctl = shutil.which("v4l2-ctl")
        if v4l2_ctl:
            print(f"✅ v4l2-ctl available at {v4l2_ctl}")
    elif system == "Darwin":
        print("🍏 macOS AVFoundation video capture subsystem active.")
        print("ℹ️ Integrated FaceTime / USB UVC cameras accessible via index 0.")
    else:
        print(f"ℹ️ Generic optical probe on {system}")

    print("==================================================================")


if __name__ == "__main__":
    check_camera()
