"""End-to-end on synthetic data: prepare -> features -> backtests -> final model -> serving bundle."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

from m5forecast.config import Config
from m5forecast.models.baselines import moving_average, seasonal_naive


def test_baselines() -> None:
    hist = np.array([[1, 2, 3, 4, 5, 6, 7, 8, 9]], dtype=float)
    assert seasonal_naive(hist, 9, season=7).tolist() == [[3, 4, 5, 6, 7, 8, 9, 3, 4]]
    assert moving_average(hist, 3, window=3).tolist() == [[8, 8, 8]]


def test_pipeline_outputs(trained: tuple[Path, Config, dict[str, object]]) -> None:
    _, cfg, result = trained
    summary = result["summary"]
    for model in ("lgbm", "seasonal_naive", "moving_average_28"):
        assert math.isfinite(summary[model]["mean"])  # type: ignore[index]

    serving = cfg.paths.reports / "serving"
    fc = pl.read_parquet(serving / "forecast.parquet")
    n_series = 10
    assert fc.height == n_series * cfg.horizon
    assert fc["forecast"].min() >= 0
    assert fc["date"].null_count() == 0
    metrics = json.loads((serving / "metrics.json").read_text(encoding="utf-8"))
    assert set(metrics["mlflow_run_ids"]) == {"baselines", "lgbm"}

    sub = pd.read_csv(cfg.paths.reports / "submission.csv")
    assert len(sub) == 2 * n_series
    assert sub["id"].str.endswith("_validation").sum() == n_series
    assert list(sub.columns) == ["id", *[f"F{i}" for i in range(1, cfg.horizon + 1)]]

    assert len(list((cfg.paths.models / "final").glob("*.txt"))) == 2
    folds = sorted((cfg.paths.reports / "backtest").glob("fold_*.parquet"))
    assert len(folds) == len(cfg.backtest_cutoffs)


def test_mlflow_runs_logged(trained: tuple[Path, Config, dict[str, object]]) -> None:
    import mlflow

    from m5forecast.config import tracking_uri

    root, cfg, result = trained
    mlflow.set_tracking_uri(tracking_uri(cfg, root))
    run = mlflow.get_run(result["run_ids"]["lgbm"])  # type: ignore[index]
    assert "lgbm_wrmsse_mean" in run.data.metrics
    assert run.data.params["num_boost_round"] == str(cfg.num_boost_round)
