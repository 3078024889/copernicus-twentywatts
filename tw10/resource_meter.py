"""Process CPU, wall time and resident memory accounting for reproducible research.

CPU seconds are process CPU time (all threads); wall seconds include waiting.
RSS is current process resident memory; peak RSS requires optional psutil polling
or platform-specific instrumentation and is deliberately not invented.
"""
from __future__ import annotations
import os
import time
from contextlib import contextmanager


def resident_bytes():
    try:
        import psutil
        return int(psutil.Process(os.getpid()).memory_info().rss)
    except (ImportError, OSError, RuntimeError):
        pass
    if os.name == 'posix':
        try:
            with open('/proc/self/statm', encoding='ascii') as f:
                pages = int(f.read().split()[1])
            return pages * os.sysconf('SC_PAGE_SIZE')
        except (OSError, ValueError, IndexError, AttributeError):
            return None
    return None


@contextmanager
def measure(target: dict):
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    start_rss = resident_bytes()
    try:
        yield
    finally:
        target.update({
            'wall_seconds': round(time.perf_counter() - start_wall, 6),
            'process_cpu_seconds': round(time.process_time() - start_cpu, 6),
            'rss_at_start_bytes': start_rss,
            'rss_at_end_bytes': resident_bytes(),
            'rss_is_peak': False,
            'measurement_scope': 'whole_process',
        })
