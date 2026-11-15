"""Turn the raw M5 CSVs into memory-safe parquet files.

Outputs (in ``paths.interim``):
  calendar.parquet          one row per day 1..1969, day number ``d`` as Int16
  prices.parquet            sell prices (Float32)
  sales_wide.parquet        bottom-level series x days 1..last_day (Int16), used by the metric
  long/<store_id>.parquet   one row per (series, day) for that store, days 1..last_day+horizon,
                            joined with calendar and price; future days have null sales

Each store is unpivoted separately so peak memory stays well under 11.7 GB.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import polars as pl

from m5forecast.config import Config, load_config

ID_COLS = ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"]
EVENT_COLS = ["event_name_1", "event_type_1", "event_name_2", "event_type_2"]


def day_columns(df: pl.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("d_")]


def read_calendar(raw: Path) -> pl.DataFrame:
    cal = pl.read_csv(raw / "calendar.csv", try_parse_dates=True)
    return cal.select(
        pl.col("d").str.strip_prefix("d_").cast(pl.Int16).alias("d"),
        pl.col("date").cast(pl.Date),
        pl.col("wm_yr_wk").cast(pl.Int32),
        pl.col("wday").cast(pl.Int8),
        pl.col("month").cast(pl.Int8),
        pl.col("year").cast(pl.Int16),
        *[pl.col(c).cast(pl.Categorical) for c in EVENT_COLS],
        *[pl.col(c).cast(pl.Int8) for c in ("snap_CA", "snap_TX", "snap_WI")],
    )


def read_prices(raw: Path) -> pl.DataFrame:
    return pl.read_csv(
        raw / "sell_prices.csv",
        schema_overrides={"wm_yr_wk": pl.Int32, "sell_price": pl.Float32},
    )


def read_sales(raw: Path, last_day: int) -> pl.DataFrame:
    sales = pl.read_csv(raw / "sales_train_evaluation.csv")
    days = day_columns(sales)
    if len(days) != last_day:
        raise ValueError(f"expected {last_day} day columns, found {len(days)}")
    return sales.with_columns(pl.col(days).cast(pl.Int16))


def store_long(
    wide: pl.DataFrame, calendar: pl.DataFrame, prices: pl.DataFrame, last_day: int, horizon: int
) -> pl.DataFrame:
    """Unpivot one store's wide sales to long rows and add the future (unknown) days."""
    days = day_columns(wide)
    long = wide.unpivot(index=ID_COLS, on=days, variable_name="d", value_name="sales").with_columns(
        pl.col("d").str.strip_prefix("d_").cast(pl.Int16)
    )
    future = (
        wide.select(ID_COLS)
        .join(
            pl.DataFrame({"d": list(range(last_day + 1, last_day + horizon + 1))}, schema={"d": pl.Int16}),
            how="cross",
        )
        .with_columns(pl.lit(None, dtype=pl.Int16).alias("sales"))
    )
    long = pl.concat([long, future.select(long.columns)])
    long = long.join(calendar, on="d", how="left").join(
        prices, on=["store_id", "item_id", "wm_yr_wk"], how="left"
    )
    return long.with_columns(pl.col(c).cast(pl.Categorical) for c in ID_COLS).sort(["id", "d"])


def prepare(cfg: Config) -> None:
    raw, out = cfg.paths.raw, cfg.paths.interim
    (out / "long").mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    calendar = read_calendar(raw)
    prices = read_prices(raw)
    sales = read_sales(raw, cfg.last_day)
    calendar.write_parquet(out / "calendar.parquet")
    prices.write_parquet(out / "prices.parquet")
    sales.write_parquet(out / "sales_wide.parquet")
    print(f"wide data: {sales.height} series x {cfg.last_day} days")

    for store in sorted(sales["store_id"].unique().to_list()):
        wide = sales.filter(pl.col("store_id") == store)
        store_long(wide, calendar, prices, cfg.last_day, cfg.horizon).write_parquet(
            out / "long" / f"{store}.parquet"
        )
        print(f"  {store}: {wide.height} series")
    print(f"prepared in {time.perf_counter() - t0:.0f}s -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    prepare(load_config(ap.parse_args().config))


if __name__ == "__main__":
    main()
