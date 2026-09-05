"""Benchmark harness infrastructure for latency, FPS, memory, GPU, CPU, thermal, storage, and accuracy."""

from typing import Final

BENCHMARK_CATEGORIES: Final[list[str]] = [
    "latency",
    "fps",
    "memory",
    "gpu",
    "cpu",
    "thermal",
    "storage",
    "accuracy",
]
