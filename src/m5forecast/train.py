"""Backtest and final training.

For every store: build features once, then for each backtest cutoff (and the final cutoff = last
known day) train a LightGBM Tweedie model on days [train_start_day, cutoff] and forecast the next
``horizon`` days. Backtests are scored with WRMSSE against the two baselines; everything is logged
to MLflow (one run for the baselines, one for LightGBM).

    uv run python -m m5forecast.train                    # full run
    uv run python -m m5forecast.train --stores CA_1 --rounds 50 --no-final   # quick smoke run
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
import polars as pl

from m5forecast.config import PROJECT_ROOT, Config, load_config, setup_mlflow
from m5forecast.data.wide import WideData
from m5forecast.features.build import CATEGORICAL, build_features, feature_names
from m5forecast.models.baselines import BASELINES


class ModelScores(TypedDict):
    per_fold: dict[int, float]
    per_level_fold1: dict[str, float]
    mean: float


Summary = dict[str, ModelScores]


def train_store(
    feats: pl.DataFrame, cfg: Config, cutoff: int, names: list[str], rounds: int
) -> tuple[lgb.Booster, pl.DataFrame]:
    h = cfg.horizon
    train = feats.filter(
        (pl.col("d") >= cfg.train_start_day)
        & (pl.col("d") <= cutoff)
        & pl.col("sales").is_not_null()
        & pl.col("sell_price").is_not_null()
    )
    data = lgb.Dataset(
        train.select(names).to_pandas(),
        label=train["sales"].to_numpy().astype(np.float32),
        categorical_feature=CATEGORICAL,
        free_raw_data=True,
    )
    booster = lgb.train(cfg.lgbm, data, num_boost_round=rounds)
    del train, data

    future = feats.filter((pl.col("d") > cutoff) & (pl.col("d") <= cutoff + h))
    pred = booster.predict(future.select(names).to_pandas())
    pred = np.where(future["sell_price"].is_null().to_numpy(), 0.0, np.clip(pred, 0, None))
    return booster, future.select("id", "d").with_columns(pl.Series("pred", pred, dtype=pl.Float32))


def to_matrix(preds: pl.DataFrame, ids: pd.DataFrame, start_day: int, horizon: int) -> np.ndarray:
    """Pivot long predictions into (series x horizon) in the evaluator's series order."""
    p = preds.with_columns(pl.col("id").cast(pl.String))
    wide = p.pivot(on="d", index="id", values="pred", sort_columns=True)
    order = pl.DataFrame({"id": ids["id"].astype(str).to_list()})
    wide = order.join(wide, on="id", how="left")
    cols = [str(d) for d in range(start_day, start_day + horizon)]
    missing = [c for c in cols if c not in wide.columns]
    if missing:
        raise ValueError(f"predictions missing days {missing[:3]}...")
    return wide.select(cols).fill_null(0.0).to_numpy().astype(np.float64)


def run(
    cfg: Config, stores: list[str] | None, rounds: int, final: bool, root: Path = PROJECT_ROOT
) -> dict[str, object]:
    t0 = time.perf_counter()
    wide = WideData.load(cfg.paths.interim)
    names = feature_names(cfg.features)
    cutoffs = list(cfg.backtest_cutoffs) + ([cfg.last_day] if final else [])
    all_stores = sorted(p.stem for p in (cfg.paths.interim / "long").glob("*.parquet"))
    stores = stores or all_stores
    subset = wide.ids["store_id"].isin(stores).to_numpy()
    ids = wide.ids[subset].reset_index(drop=True)
    sales = wide.sales[subset]
    wide_sub = WideData(ids=ids, sales=sales, prices=wide.prices, calendar=wide.calendar)

    preds: dict[int, list[pl.DataFrame]] = {c: [] for c in cutoffs}
    importance: dict[str, float] = dict.fromkeys(names, 0.0)
    model_dir = cfg.paths.models / "final"
    model_dir.mkdir(parents=True, exist_ok=True)

    for store in stores:
        ts = time.perf_counter()
        long = pl.read_parquet(cfg.paths.interim / "long" / f"{store}.parquet")
        feats = build_features(long, cfg.features, cfg.horizon)
        del long
        for c in cutoffs:
            booster, p = train_store(feats, cfg, c, names, rounds)
            preds[c].append(p)
            for n, g in zip(names, booster.feature_importance("gain"), strict=True):
                importance[n] += float(g)
            if c == cfg.last_day:
                booster.save_model(str(model_dir / f"{store}.txt"))
        del feats
        print(f"{store}: {len(cutoffs)} models in {time.perf_counter() - ts:.0f}s", flush=True)

    # ---- score backtests -------------------------------------------------------------------
    folds: dict[int, dict[str, dict[str, float]]] = {}
    reports = cfg.paths.reports
    (reports / "backtest").mkdir(parents=True, exist_ok=True)
    for c in cfg.backtest_cutoffs:
        ev = wide_sub.evaluator(c, cfg.horizon)
        actual = wide_sub.window(c + 1, cfg.horizon).astype(np.float64)
        lgbm_pred = to_matrix(pl.concat(preds[c]), ids, c + 1, cfg.horizon)
        folds[c] = {"lgbm": ev.score_levels(lgbm_pred)}
        for name, fn in BASELINES.items():
            folds[c][name] = ev.score_levels(fn(wide_sub.history(c).astype(np.float64), cfg.horizon))
        _write_fold(reports / "backtest" / f"fold_{c}.parquet", ids, c, lgbm_pred, actual)

    summary: Summary = {}
    for model in ["lgbm", *BASELINES]:
        per_fold = {c: float(np.mean(list(folds[c][model].values()))) for c in cfg.backtest_cutoffs}
        summary[model] = {
            "per_fold": per_fold,
            "per_level_fold1": folds[cfg.backtest_cutoffs[0]][model],
            "mean": float(np.mean(list(per_fold.values()))),
        }

    # ---- MLflow -----------------------------------------------------------------------------
    setup_mlflow(cfg, root)
    tags = {"stores": ",".join(stores), "python": platform.python_version()}
    run_ids = {}
    with mlflow.start_run(run_name="baselines", tags=tags) as r:
        for name in BASELINES:
            for c, s in summary[name]["per_fold"].items():
                mlflow.log_metric(f"{name}_wrmsse_cutoff_{c}", s)
            mlflow.log_metric(f"{name}_wrmsse_mean", summary[name]["mean"])
        run_ids["baselines"] = r.info.run_id
    with mlflow.start_run(run_name="lgbm-per-store", tags=tags) as r:
        mlflow.log_params({f"lgbm.{k}": v for k, v in cfg.lgbm.items()})
        mlflow.log_params(
            {
                "num_boost_round": rounds,
                "train_start_day": cfg.train_start_day,
                "lags": cfg.features.lags,
                "rolling_windows": cfg.features.rolling_windows,
                "n_features": len(names),
                "backtest_cutoffs": cfg.backtest_cutoffs,
            }
        )
        for c, s in summary["lgbm"]["per_fold"].items():
            mlflow.log_metric(f"lgbm_wrmsse_cutoff_{c}", s)
        mlflow.log_metric("lgbm_wrmsse_mean", summary["lgbm"]["mean"])
        for lvl, s in summary["lgbm"]["per_level_fold1"].items():
            mlflow.log_metric(f"lgbm_level_{lvl}_cutoff_{cfg.backtest_cutoffs[0]}", s)
        imp = pd.Series(importance).sort_values(ascending=False)
        imp_path = reports / "feature_importance.csv"
        imp.rename("gain").to_csv(imp_path, index_label="feature")
        mlflow.log_artifact(str(imp_path))
        run_ids["lgbm"] = r.info.run_id

    if final:
        _write_serving(cfg, wide_sub, pl.concat(preds[cfg.last_day]), summary, run_ids)

    elapsed = time.perf_counter() - t0
    print(json.dumps({k: v["mean"] for k, v in summary.items()}, indent=2))
    print(f"done in {elapsed / 60:.1f} min; runs {run_ids}")
    return {"summary": summary, "run_ids": run_ids}


def _write_fold(path: Path, ids: pd.DataFrame, cutoff: int, pred: np.ndarray, actual: np.ndarray) -> None:
    n, h = pred.shape
    pl.DataFrame(
        {
            "id": np.repeat(ids["id"].astype(str).to_numpy(), h),
            "store_id": np.repeat(ids["store_id"].astype(str).to_numpy(), h),
            "item_id": np.repeat(ids["item_id"].astype(str).to_numpy(), h),
            "d": np.tile(np.arange(cutoff + 1, cutoff + h + 1, dtype=np.int16), n),
            "pred": pred.reshape(-1).astype(np.float32),
            "actual": actual.reshape(-1).astype(np.float32),
        }
    ).write_parquet(path)


def _write_serving(
    cfg: Config, wide: WideData, final_preds: pl.DataFrame, summary: Summary, run_ids: dict[str, str]
) -> None:
    """Bundle that the API and dashboard read: forecasts, recent history, metrics, submission."""
    out = cfg.paths.reports / "serving"
    out.mkdir(parents=True, exist_ok=True)
    cal = wide.calendar.select(pl.col("d").cast(pl.Int16), "date")
    meta = pl.from_pandas(wide.ids.astype(str))
    fc = (
        final_preds.with_columns(pl.col("id").cast(pl.String))
        .join(meta, on="id", how="left")
        .join(cal, on="d", how="left")
        .rename({"pred": "forecast"})
    )
    fc.write_parquet(out / "forecast.parquet")

    keep = min(365, cfg.last_day)
    first = cfg.last_day - keep + 1
    n = len(wide.ids)
    hist = pl.DataFrame(
        {
            "id": np.repeat(wide.ids["id"].astype(str).to_numpy(), keep),
            "d": np.tile(np.arange(first, cfg.last_day + 1, dtype=np.int16), n),
            "sales": wide.sales[:, first - 1 : cfg.last_day].reshape(-1),
        }
    ).join(cal, on="d", how="left")
    hist.write_parquet(out / "history.parquet")

    (out / "metrics.json").write_text(
        json.dumps(
            {
                "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "horizon": cfg.horizon,
                "last_known_day": cfg.last_day,
                "backtest_cutoffs": cfg.backtest_cutoffs,
                "summary": summary,
                "mlflow_run_ids": run_ids,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    # Kaggle submission: evaluation rows = our forecast; validation rows = the known actuals of 1914-1941
    h = cfg.horizon
    fmat = to_matrix(final_preds, wide.ids, cfg.last_day + 1, h)
    known = wide.window(cfg.last_day - h + 1, h).astype(np.float64)
    cols = [f"F{i}" for i in range(1, h + 1)]
    ev_ids = wide.ids["id"].astype(str)
    sub = pd.concat(
        [
            pd.DataFrame(known, columns=cols).assign(id=ev_ids.str.replace("_evaluation", "_validation")),
            pd.DataFrame(fmat, columns=cols).assign(id=ev_ids),
        ]
    )[["id", *cols]]
    sub.to_csv(cfg.paths.reports / "submission.csv", index=False, float_format="%.4f")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    ap.add_argument("--stores", nargs="*", default=None)
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--no-final", action="store_true")
    a = ap.parse_args()
    cfg = load_config(a.config)
    run(cfg, a.stores, a.rounds or cfg.num_boost_round, final=not a.no_final)


if __name__ == "__main__":
    main()
