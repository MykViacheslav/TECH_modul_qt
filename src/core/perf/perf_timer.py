"""
Lightweight performance timer for TECH_modul.

Enabled when env TECH_PERF=1. Silent otherwise.
Output: [PERF] key=123ms
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Generator

_ENABLED: bool = os.environ.get("TECH_PERF") == "1"


def perf_log(key: str, start_ns: int) -> None:
    """Log elapsed time from *start_ns* (``time.perf_counter_ns()``)."""
    if not _ENABLED:
        return
    ms = (time.perf_counter_ns() - start_ns) / 1_000_000
    print(f"[PERF] {key}={ms:.1f}ms")


@contextmanager
def perf_scope(key: str) -> Generator[None, None, None]:
    """Context manager that logs elapsed time on exit."""
    t0 = time.perf_counter_ns()
    try:
        yield
    finally:
        perf_log(key, t0)
