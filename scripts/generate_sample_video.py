"""Generates a deterministic local test video for optical perception replay and automated integration testing."""

from pathlib import Path

import cv2
import numpy as np

from orion.core.logger import get_logger

logger = get_logger("scripts.generate_sample_video")


def generate_sample_video(
    output_path: Path | str = "assets/sample_replay.mp4",
    num_frames: int = 60,
    fps: float = 15.0,
    width: int = 640,
    height: int = 480,
) -> Path:
    """Generate or ensure sample video exists for reproducible testing."""
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    test_img_path = target_path.parent / "test_frame.jpg"
    if not test_img_path.exists():
        # Purely offline synthetic visual frame generation
        fallback = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(fallback, (100, 80), (280, 420), (180, 180, 180), -1)  # person
        cv2.circle(fallback, (190, 130), 40, (200, 200, 200), -1)  # head
        cv2.imwrite(str(test_img_path), fallback)

    base_img = cv2.imread(str(test_img_path))
    if base_img is None:
        raise RuntimeError(f"Failed to read image at {test_img_path}")

    h, w = base_img.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(target_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        shift_x = int(15 * np.sin(i / 10.0))
        shift_y = int(10 * np.cos(i / 10.0))
        m = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
        shifted = cv2.warpAffine(base_img, m, (w, h))
        resized = cv2.resize(shifted, (width, height))
        out.write(resized)

    out.release()
    logger.info("Sample test video generated", path=str(target_path), frames=num_frames)
    return target_path


if __name__ == "__main__":
    generate_sample_video()
