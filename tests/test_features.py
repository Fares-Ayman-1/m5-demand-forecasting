from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from m5forecast.config import Config, load_config
from m5forecast.data.prepare import prepare
from m5forecast.features.build import build_features, feature_names


@pytest.fixture(scope="module")
def store_long(project: tuple[Path, Config]) -> tuple[pl.DataFrame, Config]:
    _, cfg = project
    if not (cfg.paths.interim / "long" / "CA_1.parquet").exists():
        prepare(cfg)
    return pl.read_parquet(cfg.paths.interim / "long" / "CA_1.parquet"), cfg


def test_all_declared_features_exist(store_long: tuple[pl.DataFrame, Config]) -> None:
    long, cfg = store_long
    feats = build_features(long, cfg.features, cfg.horizon)
    missing = set(feature_names(cfg.features)) - set(feats.columns)
    assert not missing


def test_no_target_leakage(store_long: tuple[pl.DataFrame, Config]) -> None:
    """Features on day t must not change when sales after day t - horizon change."""
    long, cfg = store_long
    t = 120
    names = feature_names(cfg.features)
    before = build_features(long, cfg.features, cfg.horizon).filter(pl.col("d") == t).select(names)
    rng = np.random.default_rng(1)
    noisy = long.with_columns(
        pl.when(pl.col("d") > t - cfg.horizon)
        .then(pl.Series(rng.integers(0, 50, long.height)).cast(pl.Int16))
        .otherwise(pl.col("sales"))
        .alias("sales")
    )
    after = build_features(noisy, cfg.features, cfg.horizon).filter(pl.col("d") == t).select(names)
    assert before.equals(after)


def test_future_days_have_features_but_no_target(store_long: tuple[pl.DataFrame, Config]) -> None:
    long, cfg = store_long
    feats = build_features(long, cfg.features, cfg.horizon)
    future = feats.filter(pl.col("d") > cfg.last_day)
    assert future.height == feats["id"].n_unique() * cfg.horizon
    assert future["sales"].null_count() == future.height
    assert future[f"lag_{cfg.horizon}"].null_count() == 0


def test_config_rejects_leaky_lags(tmp_path: Path) -> None:
    import yaml

    from m5forecast.config import PROJECT_ROOT

    cfg = yaml.safe_load((PROJECT_ROOT / "configs" / "default.yaml").read_text(encoding="utf-8"))
    cfg["features"]["lags"] = [1, 28]
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(ValueError, match="leak"):
        load_config(p, root=tmp_path)
