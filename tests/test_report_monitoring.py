from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from m5forecast.config import Config
from m5forecast.data.wide import WideData
from m5forecast.monitoring import check, psi, to_markdown
from m5forecast.report import build


def test_psi_identical_is_zero_and_shift_is_large() -> None:
    rng = np.random.default_rng(0)
    a = rng.poisson(3, 5000).astype(float)
    assert psi(a, a.copy()) == pytest.approx(0.0, abs=1e-9)
    assert psi(a, a + 5) > 0.2


def test_monitoring_report(trained: tuple[Path, Config, dict[str, object]]) -> None:
    _, cfg, result = trained
    folds = {int(c): s for c, s in result["summary"]["lgbm"]["per_fold"].items()}  # type: ignore[index]
    r = check(cfg, WideData.load(cfg.paths.interim), folds)
    assert set(r["drift"]) == {"sales_psi", "price_psi"}
    assert isinstance(r["retrain_recommended"], bool)
    assert "Retrain recommended" in to_markdown(r)


def test_results_report_from_mlflow(trained: tuple[Path, Config, dict[str, object]]) -> None:
    root, cfg, result = trained
    md = build(cfg, root)
    lgbm_id = result["run_ids"]["lgbm"]  # type: ignore[index]
    assert f"`{lgbm_id}`" in md
    mean = result["summary"]["lgbm"]["mean"]  # type: ignore[index]
    assert f"{mean:.4f}" in md
