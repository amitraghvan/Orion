"""Performance profiling interfaces and wrapper contracts.

Architecture only: supports cProfile, PyInstrument, Memory Profiler, and Line Profiler.
Zero profiling executed.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseProfilerWrapper(ABC):
    """Abstract interface for profiler engines."""

    @abstractmethod
    def start_profiling(self) -> None:
        """Begin sampling profiler trace."""
        raise NotImplementedError(f"NOT IMPLEMENTED: {self.__class__.__name__}.start_profiling")

    @abstractmethod
    def stop_profiling(self) -> None:
        """Halt sampling profiler trace."""
        raise NotImplementedError(f"NOT IMPLEMENTED: {self.__class__.__name__}.stop_profiling")

    @abstractmethod
    def dump_stats(self, output_path: Path) -> Path:
        """Export profiler output to file."""
        raise NotImplementedError(f"NOT IMPLEMENTED: {self.__class__.__name__}.dump_stats")


class CProfileWrapper(BaseProfilerWrapper):
    """Standard Python deterministic call-graph profiler."""

    def start_profiling(self) -> None:
        raise NotImplementedError("NOT IMPLEMENTED: CProfileWrapper.start_profiling")

    def stop_profiling(self) -> None:
        raise NotImplementedError("NOT IMPLEMENTED: CProfileWrapper.stop_profiling")

    def dump_stats(self, output_path: Path) -> Path:
        raise NotImplementedError("NOT IMPLEMENTED: CProfileWrapper.dump_stats")


class PyInstrumentWrapper(BaseProfilerWrapper):
    """Statistical sampling profiler with low overhead for async loops."""

    def start_profiling(self) -> None:
        raise NotImplementedError("NOT IMPLEMENTED: PyInstrumentWrapper.start_profiling")

    def stop_profiling(self) -> None:
        raise NotImplementedError("NOT IMPLEMENTED: PyInstrumentWrapper.stop_profiling")

    def dump_stats(self, output_path: Path) -> Path:
        raise NotImplementedError("NOT IMPLEMENTED: PyInstrumentWrapper.dump_stats")


class MemoryProfilerWrapper(BaseProfilerWrapper):
    """RAM memory allocation and leak detector."""

    def start_profiling(self) -> None:
        raise NotImplementedError("NOT IMPLEMENTED: MemoryProfilerWrapper.start_profiling")

    def stop_profiling(self) -> None:
        raise NotImplementedError("NOT IMPLEMENTED: MemoryProfilerWrapper.stop_profiling")

    def dump_stats(self, output_path: Path) -> Path:
        raise NotImplementedError("NOT IMPLEMENTED: MemoryProfilerWrapper.dump_stats")


class LineProfilerWrapper(BaseProfilerWrapper):
    """Line-by-line execution time analyzer for critical inference loops."""

    def start_profiling(self) -> None:
        raise NotImplementedError("NOT IMPLEMENTED: LineProfilerWrapper.start_profiling")

    def stop_profiling(self) -> None:
        raise NotImplementedError("NOT IMPLEMENTED: LineProfilerWrapper.stop_profiling")

    def dump_stats(self, output_path: Path) -> Path:
        raise NotImplementedError("NOT IMPLEMENTED: LineProfilerWrapper.dump_stats")
