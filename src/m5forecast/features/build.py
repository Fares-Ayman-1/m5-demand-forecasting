"""Feature pipeline for one store's long frame.

Leakage rule: every feature derived from ``sales`` is shifted by at least ``horizon`` days, so the
value on day t only uses sales up to day t - horizon. One model can then forecast all ``horizon``
days at once (no recursion), and the features do not depend on the backtest cutoff, so they are
built once per store and reused for every fold. ``tests/test_features.py`` enforces the rule.
"""

from __future__ import annotations

import polars as pl

from m5forecast.config import FeatureConfig

CATEGORICAL = ["item_code", "dept_code", "cat_code", "event_name_1_code", "event_type_1_code"]


def build_features(long: pl.DataFrame, fc: FeatureConfig, horizon: int) -> pl.DataFrame:
    """Return ``long`` with feature columns added. Input must be sorted by (id, d)."""
    s = pl.col("sales").cast(pl.Float32)
    shifted = s.shift(horizon)

    lag_exprs = [s.shift(lag).over("id").alias(f"lag_{lag}") for lag in fc.lags]
    roll_exprs = []
    for w in fc.rolling_windows:
        roll_exprs.append(shifted.rolling_mean(w, min_samples=1).over("id").alias(f"rmean_{w}"))
        if w in (7, 28, 112):
            roll_exprs.append(shifted.rolling_std(w, min_samples=2).over("id").alias(f"rstd_{w}"))
    # share of zero-sales days in the last 28 known days: captures intermittency
    roll_exprs.append(
        (shifted == 0).cast(pl.Float32).rolling_mean(28, min_samples=1).over("id").alias("zero_share_28")
    )

    price = pl.col("sell_price")
    snap = (
        pl.when(pl.col("state_id") == "CA")
        .then(pl.col("snap_CA"))
        .when(pl.col("state_id") == "TX")
        .then(pl.col("snap_TX"))
        .otherwise(pl.col("snap_WI"))
    )

    out = long.with_columns(
        *lag_exprs,
        *roll_exprs,
        (price / price.max().over("id")).alias("price_norm"),
        (price / price.mean().over("id")).alias("price_mean_ratio"),
        (price / price.shift(7).over("id")).alias("price_momentum_7"),
        (price / price.mean().over(["dept_id", "d"])).alias("price_vs_dept"),
        price.n_unique().over("id").cast(pl.Int16).alias("price_n_unique"),
        snap.alias("snap"),
        pl.col("date").dt.day().cast(pl.Int8).alias("mday"),
        pl.col("date").dt.week().cast(pl.Int8).alias("week"),
        pl.col("item_id").to_physical().cast(pl.Int32).alias("item_code"),
        pl.col("dept_id").to_physical().cast(pl.Int16).alias("dept_code"),
        pl.col("cat_id").to_physical().cast(pl.Int16).alias("cat_code"),
        pl.col("event_name_1").to_physical().cast(pl.Int16).fill_null(-1).alias("event_name_1_code"),
        pl.col("event_type_1").to_physical().cast(pl.Int16).fill_null(-1).alias("event_type_1_code"),
    )
    # days since the item first had a price in this store (proxy for launch date)
    release = out.filter(price.is_not_null()).group_by("id").agg(pl.col("d").min().alias("release_d"))
    out = (
        out.join(release, on="id", how="left")
        .with_columns(
            (pl.col("d").cast(pl.Int32) - pl.col("release_d").cast(pl.Int32)).alias("days_since_release")
        )
        .drop("release_d")
    )
    return out.with_columns(pl.col(pl.Float64).cast(pl.Float32))


def feature_names(fc: FeatureConfig) -> list[str]:
    names = [f"lag_{lag}" for lag in fc.lags]
    for w in fc.rolling_windows:
        names.append(f"rmean_{w}")
        if w in (7, 28, 112):
            names.append(f"rstd_{w}")
    names += [
        "zero_share_28",
        "sell_price",
        "price_norm",
        "price_mean_ratio",
        "price_momentum_7",
        "price_vs_dept",
        "price_n_unique",
        "snap",
        "wday",
        "month",
        "mday",
        "week",
        "days_since_release",
        *CATEGORICAL,
    ]
    return names
