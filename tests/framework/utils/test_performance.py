"""Unit tests for framework performance helpers."""

from __future__ import annotations

import pytest

from framework.utils.performance import (
    is_within_budget,
    percentile,
    summarize_timings,
)

pytestmark = pytest.mark.framework_unit_test


def test_is_within_budget_returns_expected_boolean() -> None:
    assert is_within_budget(99.9, 100)
    assert is_within_budget(100, 100)
    assert not is_within_budget(100.1, 100)


def test_is_within_budget_rejects_negative_budget() -> None:
    with pytest.raises(ValueError, match="budget_ms"):
        is_within_budget(10, -1)


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([10, 20, 30, 40], 50) == 20
    assert percentile([10, 20, 30, 40], 95) == 40


def test_percentile_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="at least one timing"):
        percentile([], 95)


@pytest.mark.parametrize("rank", [0, -1, 101])
def test_percentile_rejects_invalid_rank(rank: float) -> None:
    with pytest.raises(ValueError, match="percentile_rank"):
        percentile([1], rank)


def test_summarize_timings_returns_core_metrics() -> None:
    summary = summarize_timings([10, 20, 30, 40])

    assert summary == {
        "count": 4,
        "min_ms": 10,
        "average_ms": 25,
        "p95_ms": 40,
        "max_ms": 40,
    }


def test_summarize_timings_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="at least one timing"):
        summarize_timings([])
