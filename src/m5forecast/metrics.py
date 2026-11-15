"""WRMSSE: the official M5 Accuracy metric, implemented from the competition guidelines.

For each of the 12 aggregation levels (42,840 series in total for the full data):
  RMSSE_i = sqrt( mean_h (y - yhat)^2 / mean_t (y_t - y_{t-1})^2 )
where the denominator uses the training history of series i from its first non-zero value.
Each series is weighted by its dollar sales over the last 28 training days, normalised so the
weights of one level sum to 1. WRMSSE is the mean over the 12 levels of the weighted RMSSE.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

LEVELS: list[tuple[str, list[str]]] = [
    ("total", []),
    ("state", ["state_id"]),
    ("store", ["store_id"]),
    ("category", ["cat_id"]),
    ("department", ["dept_id"]),
    ("state_category", ["state_id", "cat_id"]),
    ("state_department", ["state_id", "dept_id"]),
    ("store_category", ["store_id", "cat_id"]),
    ("store_department", ["store_id", "dept_id"]),
    ("item", ["item_id"]),
    ("item_state", ["item_id", "state_id"]),
    ("item_store", ["item_id", "store_id"]),
]


def rmsse(train: np.ndarray, actual: np.ndarray, pred: np.ndarray) -> float:
    """RMSSE of one series (reference implementation used by the tests)."""
    nz = np.flatnonzero(train != 0)
    hist = train[nz[0] :] if nz.size else train
    scale = float(np.mean(np.diff(hist) ** 2)) if hist.size > 1 else np.nan
    return float(np.sqrt(np.mean((actual - pred) ** 2) / scale))


def _group_sum(codes: np.ndarray, n_groups: int, x: np.ndarray) -> np.ndarray:
    """Sum rows of ``x`` by group code (fast path via sort + reduceat)."""
    order = np.argsort(codes, kind="stable")
    sorted_codes = codes[order]
    starts = np.flatnonzero(np.r_[True, sorted_codes[1:] != sorted_codes[:-1]])
    out = np.zeros((n_groups, *x.shape[1:]), dtype=np.float64)
    out[sorted_codes[starts]] = np.add.reduceat(x[order].astype(np.float64), starts, axis=0)
    return out


def _scales(train_agg: np.ndarray) -> np.ndarray:
    nonzero = train_agg != 0
    first = np.where(nonzero.any(axis=1), nonzero.argmax(axis=1), train_agg.shape[1])
    diffs = np.diff(train_agg, axis=1) ** 2
    t_idx = np.arange(diffs.shape[1])[None, :]
    valid = t_idx >= first[:, None]  # diff (t+1) - t counts once t >= first non-zero index
    count = valid.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, (diffs * valid).sum(axis=1) / count, np.nan)


@dataclass
class _Level:
    name: str
    codes: np.ndarray
    n: int
    scale: np.ndarray
    weight: np.ndarray
    actual: np.ndarray


class WRMSSEEvaluator:
    """Precomputes scales and weights for one cutoff, then scores any number of forecasts."""

    def __init__(self, ids: pd.DataFrame, train: np.ndarray, actual: np.ndarray, revenue: np.ndarray):
        if not (len(ids) == train.shape[0] == actual.shape[0] == revenue.shape[0]):
            raise ValueError("ids, train, actual and revenue must have the same number of series")
        self.horizon = actual.shape[1]
        self.levels: list[_Level] = []
        for name, cols in LEVELS:
            if cols:
                codes, uniques = pd.MultiIndex.from_frame(ids[cols]).factorize()
                n = len(uniques)
            else:
                codes, n = np.zeros(len(ids), dtype=np.int64), 1
            codes = np.asarray(codes, dtype=np.int64)
            rev = _group_sum(codes, n, revenue.reshape(-1, 1))[:, 0]
            scale = _scales(_group_sum(codes, n, train))
            usable = np.isfinite(scale) & (scale > 0)
            weight = np.where(usable, rev, 0.0)
            weight = weight / weight.sum() if weight.sum() > 0 else weight
            self.levels.append(
                _Level(name, codes, n, np.where(usable, scale, 1.0), weight, _group_sum(codes, n, actual))
            )

    def score_levels(self, pred: np.ndarray) -> dict[str, float]:
        if pred.shape != (self.levels[0].codes.shape[0], self.horizon):
            raise ValueError(f"prediction shape {pred.shape} does not match the evaluator")
        out = {}
        for lv in self.levels:
            p = _group_sum(lv.codes, lv.n, pred)
            r = np.sqrt(np.mean((lv.actual - p) ** 2, axis=1) / lv.scale)
            out[lv.name] = float(np.sum(lv.weight * r))
        return out

    def score(self, pred: np.ndarray) -> float:
        return float(np.mean(list(self.score_levels(pred).values())))
