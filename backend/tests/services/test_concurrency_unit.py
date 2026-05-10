from __future__ import annotations

import time

import pytest

from app.services.concurrency import run_in_parallel


def test_empty_input_returns_empty_list() -> None:
    assert run_in_parallel() == []


def test_single_callable_returns_in_list() -> None:
    assert run_in_parallel(lambda: 42) == [42]


def test_results_preserve_input_order() -> None:
    results = run_in_parallel(
        lambda: "a",
        lambda: "b",
        lambda: "c",
    )
    assert results == ["a", "b", "c"]


def test_callables_run_concurrently() -> None:
    sleep_seconds = 0.2

    def slow(value: str) -> str:
        time.sleep(sleep_seconds)
        return value

    started = time.perf_counter()
    results = run_in_parallel(
        lambda: slow("a"),
        lambda: slow("b"),
        lambda: slow("c"),
    )
    elapsed = time.perf_counter() - started

    assert results == ["a", "b", "c"]
    # Sequential would take ~0.6s; concurrent should finish well under that.
    assert elapsed < sleep_seconds * 2, f"expected concurrent execution, took {elapsed:.3f}s"


def test_default_worker_count_is_capped() -> None:
    sleep_seconds = 0.12

    def slow(value: int) -> int:
        time.sleep(sleep_seconds)
        return value

    started = time.perf_counter()
    results = run_in_parallel(
        lambda: slow(1),
        lambda: slow(2),
        lambda: slow(3),
        lambda: slow(4),
    )
    elapsed = time.perf_counter() - started

    assert results == [1, 2, 3, 4]
    assert sleep_seconds * 2 <= elapsed < sleep_seconds * 3


def test_exception_propagates() -> None:
    def boom() -> None:
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError, match="nope"):
        run_in_parallel(lambda: 1, boom, lambda: 3)
