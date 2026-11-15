"""Tiny synthetic dataset in the exact M5 file format.

The whole pipeline runs on it in CI, without the Kaggle data.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

STORES = {"CA_1": "CA", "TX_1": "TX"}
ITEMS = {
    "HOBBIES_1_001": "HOBBIES_1",
    "HOBBIES_1_002": "HOBBIES_1",
    "FOODS_1_001": "FOODS_1",
    "FOODS_1_002": "FOODS_1",
    "FOODS_1_003": "FOODS_1",
}
LAST_DAY, HORIZON = 140, 7


def write_raw(raw: Path, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    raw.mkdir(parents=True, exist_ok=True)
    n_days = LAST_DAY + HORIZON
    start = date(2011, 1, 29)
    days = np.arange(1, n_days + 1)
    cal = pd.DataFrame(
        {
            "date": [start + timedelta(days=int(d - 1)) for d in days],
            "wm_yr_wk": 11101 + (days - 1) // 7,
            "weekday": "x",
            "wday": (days - 1) % 7 + 1,
            "month": [(start + timedelta(days=int(d - 1))).month for d in days],
            "year": [(start + timedelta(days=int(d - 1))).year for d in days],
            "d": [f"d_{d}" for d in days],
            "event_name_1": np.where(days % 45 == 0, "SuperBowl", None),
            "event_type_1": np.where(days % 45 == 0, "Sporting", None),
            "event_name_2": None,
            "event_type_2": None,
            "snap_CA": (days % 10 < 3).astype(int),
            "snap_TX": (days % 10 < 2).astype(int),
            "snap_WI": 0,
        }
    )
    cal.to_csv(raw / "calendar.csv", index=False)

    rows, prices = [], []
    weeks = sorted(cal["wm_yr_wk"].unique())
    for store, state in STORES.items():
        for k, (item, dept) in enumerate(ITEMS.items()):
            release = 20 if item.endswith("003") else 1  # one item launches later
            base = 1.0 + k
            season = 1 + 0.4 * np.sin(2 * np.pi * days[:LAST_DAY] / 7)
            y = rng.poisson(base * season)
            y[: release - 1] = 0
            rows.append(
                {
                    "id": f"{item}_{store}_evaluation",
                    "item_id": item,
                    "dept_id": dept,
                    "cat_id": dept.split("_")[0],
                    "store_id": store,
                    "state_id": state,
                    **{f"d_{d}": int(v) for d, v in zip(days[:LAST_DAY], y, strict=True)},
                }
            )
            for w in weeks:
                if (w - 11101) * 7 + 7 >= release:
                    prices.append(
                        {
                            "store_id": store,
                            "item_id": item,
                            "wm_yr_wk": w,
                            "sell_price": round(2.0 + k + 0.1 * ((w - 11101) % 3), 2),
                        }
                    )
    pd.DataFrame(rows).to_csv(raw / "sales_train_evaluation.csv", index=False)
    pd.DataFrame(prices).to_csv(raw / "sell_prices.csv", index=False)
    pd.DataFrame({"id": [r["id"] for r in rows]}).to_csv(raw / "sample_submission.csv", index=False)


def write_config(root: Path) -> Path:
    cfg = {
        "competition": "synthetic",
        "paths": {"raw": "data/raw", "interim": "data/interim", "models": "models", "reports": "reports"},
        "tracking_uri": str((root / "mlflow.db").resolve()),
        "artifact_root": str((root / "mlruns").resolve()),
        "experiment": "test",
        "horizon": HORIZON,
        "last_day": LAST_DAY,
        "backtest_cutoffs": [LAST_DAY - 7, LAST_DAY - 14],
        "train_start_day": 40,
        "features": {"lags": [7, 8, 14], "rolling_windows": [7, 14, 28]},
        "lgbm": {
            "objective": "tweedie",
            "tweedie_variance_power": 1.1,
            "learning_rate": 0.1,
            "num_leaves": 7,
            "min_data_in_leaf": 5,
            "num_threads": 2,
            "seed": 1,
            "verbose": -1,
        },
        "num_boost_round": 20,
    }
    path = root / "configs" / "test.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path
