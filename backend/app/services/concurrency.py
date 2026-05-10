from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")
DEFAULT_MAX_WORKERS = 3


def run_in_parallel(*callables: Callable[[], T], max_workers: int = DEFAULT_MAX_WORKERS) -> list[T]:
    """Run zero-arg callables concurrently and return results in input order.

    Each callable runs in its own thread; results are collected in the same
    order they were submitted. The first exception encountered (in submission
    order) is re-raised once all submitted work has completed.

    Use this for I/O-bound fan-out (e.g. independent Gemini calls inside a
    request). For a single callable this short-circuits to an in-line call.
    """

    if not callables:
        return []
    if len(callables) == 1:
        return [callables[0]()]
    workers = min(max_workers, len(callables))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fn) for fn in callables]
        return [future.result() for future in futures]
