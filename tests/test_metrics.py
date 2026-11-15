"""The metric is checked against values worked out by hand (see comments)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from m5forecast.metrics import LEVELS, WRMSSEEvaluator, rmsse


def test_rmsse_hand_calculated() -> None:
    # history from first non-zero value: [1, 3, 2] -> squared diffs [4, 1] -> scale 2.5
    # errors: actual [2, 4] vs pred [3, 4] -> mse 0.5 -> sqrt(0.5 / 2.5) = sqrt(0.2)
    assert rmsse(np.array([0, 1, 3, 2.0]), np.array([2, 4.0]), np.array([3, 4.0])) == pytest.approx(
        np.sqrt(0.2)
    )


def _two_series() -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    ids = pd.DataFrame(
        {
            "id": ["A_S1", "B_S1"],
            "item_id": ["A", "B"],
            "dept_id": ["D1", "D1"],
            "cat_id": ["C1", "C1"],
            "store_id": ["S1", "S1"],
            "state_id": ["X", "X"],
        }
    )
    train = np.array([[0, 1, 3, 2], [1, 1, 1, 3]], dtype=float)
    actual = np.array([[2, 4], [3, 3]], dtype=float)
    return ids, train, actual


def test_wrmsse_hand_calculated() -> None:
    ids, train, actual = _two_series()
    pred = np.array([[3, 4], [3, 3]], dtype=float)
    ev = WRMSSEEvaluator(ids, train, actual, revenue=np.array([1.0, 1.0]))
    # Levels 1-9 aggregate both items into one series: train [1, 2, 4, 5] -> scale (1+4+1)/3 = 2;
    # actual [5, 7] vs pred [6, 7] -> mse 0.5 -> RMSSE sqrt(0.25) = 0.5, weight 1.
    # Levels 10-12 keep A and B apart: A = sqrt(0.2), B = 0 (perfect), equal weights -> sqrt(0.2) / 2.
    expected = (9 * 0.5 + 3 * np.sqrt(0.2) / 2) / 12
    levels = ev.score_levels(pred)
    assert len(levels) == len(LEVELS) == 12
    assert levels["total"] == pytest.approx(0.5)
    assert levels["item_store"] == pytest.approx(np.sqrt(0.2) / 2)
    assert ev.score(pred) == pytest.approx(expected)


def test_perfect_forecast_scores_zero() -> None:
    ids, train, actual = _two_series()
    assert WRMSSEEvaluator(ids, train, actual, np.array([3.0, 1.0])).score(actual.copy()) == pytest.approx(
        0.0
    )


def test_weights_follow_revenue() -> None:
    ids, train, actual = _two_series()
    pred = np.array([[3, 4], [3, 3]], dtype=float)
    # All revenue on A: bottom levels score only A's error.
    ev = WRMSSEEvaluator(ids, train, actual, revenue=np.array([5.0, 0.0]))
    assert ev.score_levels(pred)["item_store"] == pytest.approx(np.sqrt(0.2))


def test_shape_mismatch_raises() -> None:
    ids, train, actual = _two_series()
    ev = WRMSSEEvaluator(ids, train, actual, np.array([1.0, 1.0]))
    with pytest.raises(ValueError):
        ev.score(np.zeros((2, 3)))
