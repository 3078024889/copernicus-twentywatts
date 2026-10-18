"""Bounded process resource instrumentation for research experiments.

Measures wall time, process CPU time, Python traced peak allocation, and sampled
process RSS peak. RSS is sampled, so a peak shorter than the sampling interval
can be missed. Operation counts must be incremented explicitly by the caller.
"""
from __future__ import annotations

import os
import threading
import time
import tracemalloc
from functools import wraps
from dataclasses import dataclass, asdict
from typing import Any

_ACTIVE = threading.local()

def count_operation(n: int = 1) -> None:
    """Count explicit algorithm API calls inside the active ResourceMeter.

    This is a semantic call counter, NOT a hardware FLOP/instruction counter.
    """
    meter = getattr(_ACTIVE, "meter", None)
    if meter is not None:
        meter.count_operations(n)

def measured_evaluation(func):
    """Measure one evaluation call and attach an auditable report to its result."""
    @wraps(func)
    def wrapped(*args, **kwargs):
        meter = ResourceMeter(operation_count_source="instrumented_algorithm_api_calls_v1")
        with meter:
            result = func(*args, **kwargs)
        if isinstance(result, dict):
            result["resource_measurement"] = meter.report()
            result["operation_count_semantics"] = (
                "Count of instrumented predict/update API invocations; not FLOPs or machine instructions."
            )
        return result
    return wrapped


def _rss_bytes():
    """Return current process resident memory in bytes, or None if unavailable."""
    import os

    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            SIZE_T = ctypes.c_size_t

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", SIZE_T),
                    ("WorkingSetSize", SIZE_T),
                    ("QuotaPeakPagedPoolUsage", SIZE_T),
                    ("QuotaPagedPoolUsage", SIZE_T),
                    ("QuotaPeakNonPagedPoolUsage", SIZE_T),
                    ("QuotaNonPagedPoolUsage", SIZE_T),
                    ("PagefileUsage", SIZE_T),
                    ("PeakPagefileUsage", SIZE_T),
                ]

            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            get_current_process = kernel32.GetCurrentProcess
            get_current_process.argtypes = []
            get_current_process.restype = wintypes.HANDLE

            get_memory = psapi.GetProcessMemoryInfo
            get_memory.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
                wintypes.DWORD,
            ]
            get_memory.restype = wintypes.BOOL

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)

            ok = get_memory(
                get_current_process(),
                ctypes.byref(counters),
                counters.cb,
            )
            if not ok:
                return None

            value = int(counters.WorkingSetSize)
            return value if value >= 0 else None
        except (AttributeError, OSError, TypeError, ValueError):
            return None

    try:
        with open("/proc/self/statm", "r", encoding="ascii") as stream:
            fields = stream.read().split()
        if len(fields) < 2:
            return None
        import os
        value = int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
        return value if value >= 0 else None
    except (OSError, ValueError, IndexError, AttributeError):
        pass

    try:
        import psutil
        value = int(psutil.Process().memory_info().rss)
        return value if value >= 0 else None
    except (ImportError, OSError, ValueError, AttributeError):
        return None



@dataclass
class ResourceMeasurement:
    wall_seconds: float
    process_cpu_seconds: float
    peak_traced_bytes: int
    peak_sampled_rss_bytes: int | None
    rss_sampling_interval_ms: float
    operation_count: int
    operation_count_source: str
    complete: bool
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ResourceMeter:
    """Context manager; call count_operations(n) at the operation boundary."""

    def __init__(self, *, rss_interval_ms: float = 5.0, operation_count_source: str = "caller"):
        if not (0.5 <= rss_interval_ms <= 1000):
            raise ValueError("rss_interval_ms must be within [0.5, 1000]")
        if not operation_count_source.strip():
            raise ValueError("operation_count_source must be non-empty")
        self.interval = rss_interval_ms / 1000.0
        self.operation_count_source = operation_count_source
        self.operation_count = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._peak_rss: int | None = None
        self._wall_start = 0.0
        self._cpu_start = 0.0
        self._tracing_started_here = False
        self._previous_meter = None
        self._rss_samples = 0
        self._rss_available = False
        self._traced_baseline = 0
        self.result: ResourceMeasurement | None = None

    def count_operations(self, n: int = 1) -> None:
        if type(n) is not int or n < 0:
            raise ValueError("operation increment must be a non-negative integer")
        self.operation_count += n

    def _sample(self) -> None:
        while not self._stop.is_set():
            value = _rss_bytes()
            if value is not None:
                self._rss_available = True
                self._rss_samples += 1
                self._peak_rss = value if self._peak_rss is None else max(self._peak_rss, value)
            self._stop.wait(self.interval)

    def __enter__(self):
        self._wall_start = time.perf_counter()
        self._cpu_start = time.process_time()
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._tracing_started_here = True
        self._traced_baseline = tracemalloc.get_traced_memory()[0]
        tracemalloc.reset_peak()
        self._peak_rss = _rss_bytes()
        if self._peak_rss is not None:
            self._rss_available = True
            self._rss_samples = 1
        self._previous_meter = getattr(_ACTIVE, "meter", None)
        _ACTIVE.meter = self
        self._thread = threading.Thread(target=self._sample, name="tw-resource-sampler", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        wall = time.perf_counter() - self._wall_start
        cpu = time.process_time() - self._cpu_start
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval * 4))
        _, traced_peak = tracemalloc.get_traced_memory()
        _ACTIVE.meter = self._previous_meter
        if self._tracing_started_here:
            tracemalloc.stop()
        limitations = [
            "RSS peak is sampled and may miss shorter spikes.",
            "Python traced allocation is not total process memory.",
            "No GPU time, energy, or hardware FLOP counter is measured.",
            "Operation count is caller-supplied, not inferred from machine instructions.",
        ]
        self.result = ResourceMeasurement(
            wall_seconds=wall,
            process_cpu_seconds=cpu,
            peak_traced_bytes=max(0, int(traced_peak) - self._traced_baseline),
            peak_sampled_rss_bytes=self._peak_rss,
            rss_sampling_interval_ms=self.interval * 1000,
            operation_count=self.operation_count,
            operation_count_source=self.operation_count_source,
            complete=(exc_type is None),
            limitations=limitations,
        )
        return False

    def report(self) -> dict[str, Any]:
        if self.result is None:
            raise RuntimeError("ResourceMeter has not exited its context")
        payload = self.result.to_dict()
        payload["rss_sample_count"] = self._rss_samples
        payload["rss_available"] = self._rss_available
        payload["operation_count_semantics"] = "instrumented predict/update API invocations; not FLOPs or machine instructions"
        return payload
