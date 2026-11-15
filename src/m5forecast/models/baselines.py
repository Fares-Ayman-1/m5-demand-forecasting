"""Simple reference forecasts every model must beat. Inputs are (series x days) arrays of known history."""

from __future__ import annotations

import numpy as np


def seasonal_naive(history: np.ndarray, horizon: int, season: int = 7) -> np.ndarray:
    """Repeat the last observed week."""
    last = history[:, -season:]
    reps = int(np.ceil(horizon / season))
    return np.tile(last, (1, reps))[:, :horizon].astype(np.float64)


def moving_average(history: np.ndarray, horizon: int, window: int = 28) -> np.ndarray:
    """Flat forecast at the mean of the last ``window`` days."""
    level = history[:, -window:].mean(axis=1, keepdims=True)
    return np.repeat(level, horizon, axis=1).astype(np.float64)


BASELINES = {"seasonal_naive": seasonal_naive, "moving_average_28": moving_average}
