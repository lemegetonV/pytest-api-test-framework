"""Small performance helpers for API test assertions."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import mean
from time import perf_counter
from typing import Callable, Generic, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class TimedResult(Generic[T]):
    """Return value and elapsed time captured from one measured operation."""

    value: T
    elapsed_ms: float


def measure_call(operation: Callable[[], T]) -> TimedResult[T]:
    """Run an operation once and return its value with elapsed milliseconds."""
    start = perf_counter()
    value = operation()
    end = perf_counter()
    return TimedResult(value=value, elapsed_ms=(end - start) * 1000)


def is_within_budget(elapsed_ms: float, budget_ms: float) -> bool:
    """Return whether one elapsed time is inside a response-time budget."""
    if budget_ms < 0:
        raise ValueError("budget_ms must be zero or greater")
    return elapsed_ms <= budget_ms


def percentile(values: Sequence[float], percentile_rank: float) -> float:
    """Return a nearest-rank percentile from a non-empty timing sample."""
    if not values:
        raise ValueError("values must contain at least one timing")
    if not 0 < percentile_rank <= 100:
        raise ValueError("percentile_rank must be greater than 0 and at most 100")

    sorted_values = sorted(values)
    index = ceil((percentile_rank / 100) * len(sorted_values)) - 1
    return sorted_values[index]


def summarize_timings(elapsed_values_ms: Sequence[float]) -> dict[str, float | int]:
    """Summarize a timing sample for learning-level performance checks."""
    if not elapsed_values_ms:
        raise ValueError("elapsed_values_ms must contain at least one timing")

    return {
        "count": len(elapsed_values_ms),
        "min_ms": min(elapsed_values_ms),
        "average_ms": mean(elapsed_values_ms),
        "p95_ms": percentile(elapsed_values_ms, 95),
        "max_ms": max(elapsed_values_ms),
    }
