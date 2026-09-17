"""Automated Camera Diagnostic Tool for ORION BAS AI Copilot.

Queries local optical capture devices via OpenCV, audits device indices,
verifies resolutions, measures instantaneous FPS and frame read latency.
"""

import sys
import time

import cv2


def test_camera(max_devices: int = 4) -> int:
    print("==================================================================")
    print("📷 ORION BAS AI COPILOT — CAMERA DIAGNOSTIC PROBE")
    print("==================================================================")

    found_any = False

    for idx in range(max_devices):
        print(f"\nProbing Camera Device Index [{idx}]...")
        t0 = time.perf_counter()
        cap = cv2.VideoCapture(idx)

        if not cap.isOpened():
            print(f"  Camera {idx}: UNAVAILABLE (Failed to open)")
            cap.release()
            continue

        found_any = True
        open_latency_ms = (time.perf_counter() - t0) * 1000.0

        # Attempt to read frame
        t_read_start = time.perf_counter()
        ret, frame = cap.read()
        read_latency_ms = (time.perf_counter() - t_read_start) * 1000.0

        if not ret or frame is None:
            print(f"  Camera {idx}: OPEN: OK, FRAME READ: FAILED")
            cap.release()
            continue

        h, w, c = frame.shape
        fps_reported = cap.get(cv2.CAP_PROP_FPS)

        # Benchmark 10 consecutive frame reads to compute real measured FPS and average latency
        latencies = []
        for _ in range(10):
            t_f = time.perf_counter()
            ret_f, _ = cap.read()
            if ret_f:
                latencies.append((time.perf_counter() - t_f) * 1000.0)

        avg_lat_ms = sum(latencies) / len(latencies) if latencies else read_latency_ms
        measured_fps = (
            1000.0 / avg_lat_ms if avg_lat_ms > 0 else (fps_reported if fps_reported > 0 else 30.0)
        )

        print(f"  Camera {idx}")
        print("  OPEN:       OK")
        print("  FRAME:      OK")
        print(f"  RESOLUTION: {w}x{h} ({c} channels, {frame.dtype})")
        print(f"  FPS:        {measured_fps:.1f} (Reported: {fps_reported:.1f})")
        print(f"  LATENCY:    {avg_lat_ms:.1f}ms (Init: {open_latency_ms:.1f}ms)")

        cap.release()

    print("\n==================================================================")
    if found_any:
        print("✅ Camera diagnostic completed: At least one optical sensor active.")
        print("==================================================================")
        return 0
    print("❌ No operational optical camera discovered.")
    print("==================================================================")
    return 1


if __name__ == "__main__":
    sys.exit(test_camera())
