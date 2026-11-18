"""Aggregate the M5 data and backtest output into the small JSON files the video draws.

Run from the project root with the project's environment:

    uv run --no-sync python video/scripts/extract.py

Reads data/interim/sales_wide.parquet, data/interim/calendar.parquet and
reports/backtest/fold_1913.parquet with lazy scans (needed columns only) and writes
video/public/data/m5.json. The output is derived from the competition data, so it is git-ignored.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("POLARS_MAX_THREADS", "2")  # shared laptop: keep the footprint small

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
WIDE = ROOT / "data" / "interim" / "sales_wide.parquet"
CAL = ROOT / "data" / "interim" / "calendar.parquet"
FOLD_CUTOFF = 1913
FOLD = ROOT / "reports" / "backtest" / f"fold_{FOLD_CUTOFF}.parquet"
OUT = ROOT / "video" / "public" / "data" / "m5.json"

CONTEXT_DAYS = 56  # history shown before the backtest window
HOOK_WEEKS = 277  # 277 full weeks = days 1..1939
LEVELS = [  # same order and grouping as src/m5forecast/metrics.py LEVELS
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


def r(x: float, nd: int = 1) -> float:
    return round(float(x), nd)


def main() -> None:
    wide = pl.scan_parquet(WIDE)
    names = wide.collect_schema().names()
    day_cols = [c for c in names if c.startswith("d_")]
    n_days = len(day_cols)
    first_day, last_day = int(day_cols[0][2:]), int(day_cols[-1][2:])

    keys = wide.select("id", "item_id", "dept_id", "cat_id", "store_id", "state_id").collect()
    level_counts = [
        {"level": name, "n": 1 if not cols else keys.select(cols).unique().height} for name, cols in LEVELS
    ]

    cal = pl.read_parquet(CAL, columns=["d", "date"])
    date_of = {int(d): str(dt) for d, dt in zip(cal["d"], cal["date"], strict=True)}

    # Hook: weekly unit sales for every store x department (70 series), each scaled to its own max.
    sd = (
        wide.group_by("store_id", "dept_id")
        .agg(pl.col(day_cols[: HOOK_WEEKS * 7]).cast(pl.Int32).sum())
        .sort("store_id", "dept_id")
        .collect()
    )
    mat = sd.select(day_cols[: HOOK_WEEKS * 7]).to_numpy().astype(np.float64)
    weekly = mat.reshape(mat.shape[0], HOOK_WEEKS, 7).sum(axis=2)
    weekly /= np.maximum(weekly.max(axis=1, keepdims=True), 1)
    hook = [[r(v, 3) for v in row] for row in weekly]

    # Daily total of all 30,490 series, days 1..last_day (problem scene timeline).
    total_daily = wide.select(pl.col(day_cols).cast(pl.Int32).sum()).collect().row(0)

    # Backtest window after the cutoff: total over all series, and one item-store series.
    fold = pl.scan_parquet(FOLD).select("id", "d", "pred", "actual")
    tot = fold.group_by("d").agg(pl.col("pred").sum(), pl.col("actual").sum()).sort("d").collect()
    top = (
        fold.group_by("id")
        .agg(pl.col("actual").sum())
        .sort("actual", descending=True)
        .head(1)
        .collect()["id"][0]
    )
    one = fold.filter(pl.col("id") == top).sort("d").collect()
    ctx_cols = [f"d_{d}" for d in range(FOLD_CUTOFF - CONTEXT_DAYS + 1, FOLD_CUTOFF + 1)]
    ctx_total = wide.select(pl.col(ctx_cols).cast(pl.Int32).sum()).collect().row(0)
    ctx_one = wide.filter(pl.col("id") == top).select(ctx_cols).collect().row(0)

    def mape_like(a: np.ndarray, p: np.ndarray) -> float:
        return float(np.abs(a - p).sum() / a.sum())

    out = {
        "n_series": keys.height,
        "n_stores": keys["store_id"].n_unique(),
        "n_states": keys["state_id"].n_unique(),
        "states": sorted(keys["state_id"].unique().to_list()),
        "stores": sorted(keys["store_id"].unique().to_list()),
        "first_day": first_day,
        "last_day": last_day,
        "n_days": n_days,
        "first_date": date_of[first_day],
        "last_date": date_of[last_day],
        "dates": {str(d): date_of[d] for d in (1857, 1858, 1885, 1886, 1913, 1914, 1941, 1942, 1969)},
        "levels": level_counts,
        "n_level_series": sum(x["n"] for x in level_counts),
        "hook": {"n": len(hook), "weeks": HOOK_WEEKS, "lines": hook},
        "total_daily": list(total_daily),
        "fold": {
            "cutoff": FOLD_CUTOFF,
            "context_days": CONTEXT_DAYS,
            "days": tot["d"].to_list(),
            "total": {
                "history": list(ctx_total),
                "pred": [r(v) for v in tot["pred"]],
                "actual": [r(v, 0) for v in tot["actual"]],
                "abs_err_share": r(mape_like(tot["actual"].to_numpy(), tot["pred"].to_numpy()), 4),
            },
            "item": {
                "id": top.removesuffix("_evaluation"),
                "why": "highest unit sales of all 30,490 series in this window",
                "history": list(ctx_one),
                "pred": [r(v, 2) for v in one["pred"]],
                "actual": [r(v, 0) for v in one["actual"]],
            },
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB); item series: {top}")


if __name__ == "__main__":
    main()
