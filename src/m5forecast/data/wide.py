"""Helpers on the wide (series x days) sales table used by the metric and baselines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

from m5forecast.data.prepare import ID_COLS
from m5forecast.metrics import WRMSSEEvaluator


@dataclass
class WideData:
    ids: pd.DataFrame  # one row per bottom-level series, in a fixed order
    sales: np.ndarray  # (series, days) int16, column j = day j + 1
    prices: pl.DataFrame
    calendar: pl.DataFrame

    @classmethod
    def load(cls, interim: Path) -> WideData:
        wide = pl.read_parquet(interim / "sales_wide.parquet")
        day_cols = [c for c in wide.columns if c.startswith("d_")]
        return cls(
            ids=wide.select(ID_COLS).to_pandas(),
            sales=wide.select(day_cols).to_numpy().astype(np.int16),
            prices=pl.read_parquet(interim / "prices.parquet"),
            calendar=pl.read_parquet(interim / "calendar.parquet"),
        )

    def history(self, cutoff: int) -> np.ndarray:
        return self.sales[:, :cutoff]

    def window(self, start_day: int, horizon: int) -> np.ndarray:
        return self.sales[:, start_day - 1 : start_day - 1 + horizon]

    def revenue(self, cutoff: int, days: int = 28) -> np.ndarray:
        """Dollar sales per series over the ``days`` days ending at ``cutoff`` (the metric weights)."""
        first = cutoff - days + 1
        units = pl.DataFrame(
            {
                "id": np.repeat(self.ids["id"].to_numpy(), days),
                "store_id": np.repeat(self.ids["store_id"].to_numpy(), days),
                "item_id": np.repeat(self.ids["item_id"].to_numpy(), days),
                "d": np.tile(np.arange(first, cutoff + 1, dtype=np.int16), len(self.ids)),
                "units": self.sales[:, first - 1 : cutoff].reshape(-1).astype(np.float64),
            }
        )
        wk = self.calendar.select(pl.col("d").cast(pl.Int16), "wm_yr_wk")
        rev = (
            units.join(wk, on="d", how="left")
            .join(self.prices, on=["store_id", "item_id", "wm_yr_wk"], how="left")
            .group_by("id", maintain_order=True)
            .agg((pl.col("units") * pl.col("sell_price").fill_null(0.0)).sum().alias("revenue"))
        )
        lookup = dict(zip(rev["id"].to_list(), rev["revenue"].to_list(), strict=True))
        return np.array([lookup[i] for i in self.ids["id"]], dtype=np.float64)

    def evaluator(self, cutoff: int, horizon: int) -> WRMSSEEvaluator:
        return WRMSSEEvaluator(
            self.ids,
            self.history(cutoff).astype(np.float64),
            self.window(cutoff + 1, horizon).astype(np.float64),
            self.revenue(cutoff),
        )
