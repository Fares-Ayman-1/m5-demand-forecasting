"""Write RESULTS.md from the latest MLflow runs, so every published number traces back to a run.

uv run python -m m5forecast.report
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import mlflow

from m5forecast.config import PROJECT_ROOT, Config, load_config, setup_mlflow
from m5forecast.metrics import LEVELS

MODEL_LABEL = {
    "lgbm": "LightGBM, Tweedie, one model per store",
    "seasonal_naive": "Seasonal naive (repeat last week)",
    "moving_average_28": "Moving average (last 28 days)",
}


def latest_run(exp_id: str, name: str) -> mlflow.entities.Run:
    runs = mlflow.search_runs(
        experiment_ids=[exp_id],
        filter_string=f"attributes.run_name = '{name}' and attributes.status = 'FINISHED'",
        order_by=["attributes.start_time DESC"],
        max_results=1,
        output_format="list",
    )
    if not runs:
        raise SystemExit(f"no finished '{name}' run in MLflow; run `python -m m5forecast.train` first")
    return runs[0]


def build(cfg: Config, root: Path = PROJECT_ROOT) -> str:
    exp_id = setup_mlflow(cfg, root)
    lgbm, base = latest_run(exp_id, "lgbm-per-store"), latest_run(exp_id, "baselines")
    cut = cfg.backtest_cutoffs

    def metric(run: mlflow.entities.Run, key: str) -> float:
        return float(run.data.metrics[key])

    rows = []
    for model, run in (("lgbm", lgbm), ("seasonal_naive", base), ("moving_average_28", base)):
        folds = [metric(run, f"{model}_wrmsse_cutoff_{c}") for c in cut]
        mean = metric(run, f"{model}_wrmsse_mean")
        rows.append((model, folds, mean, run.info.run_id))
    best_base = min(r[2] for r in rows if r[0] != "lgbm")
    gain = 1 - rows[0][2] / best_base

    fold_hdr = " | ".join(f"days {c + 1}–{c + cfg.horizon}" for c in cut)
    L = [
        "# Results",
        "",
        f"Generated from MLflow on {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `python -m m5forecast.report`.",
        "Metric: **WRMSSE** (the official M5 Accuracy metric; lower is better), on "
        f"{len(cut)} rolling {cfg.horizon}-day backtests over every series of the stores listed below.",
        "Every number below is a logged MLflow metric of the run shown.",
        "",
        f"| Model | {fold_hdr} | Mean | MLflow run |",
        "|---|" + "---:|" * (len(cut) + 1) + "---|",
    ]
    for model, folds, mean, rid in rows:
        L.append(
            f"| {MODEL_LABEL[model]} | "
            + " | ".join(f"{f:.4f}" for f in folds)
            + f" | **{mean:.4f}** | `{rid}` |"
        )
    L += [
        "",
        f"LightGBM lowers mean WRMSSE by **{gain:.1%}** relative to the best baseline.",
        "",
        f"## WRMSSE by aggregation level (backtest days {cut[0] + 1}–{cut[0] + cfg.horizon})",
        "",
        "| Level | LightGBM |",
        "|---|---:|",
    ]
    for name, _ in LEVELS:
        L.append(f"| {name.replace('_', ' × ')} | {metric(lgbm, f'lgbm_level_{name}_cutoff_{cut[0]}'):.4f} |")

    p = lgbm.data.params
    L += [
        "",
        "## Training setup (from the run's parameters)",
        "",
        f"- Boosting rounds: {p.get('num_boost_round')}; learning rate {p.get('lgbm.learning_rate')}; "
        f"leaves {p.get('lgbm.num_leaves')}; Tweedie power {p.get('lgbm.tweedie_variance_power')}",
        f"- Training rows from day {p.get('train_start_day')}; {p.get('n_features')} features; "
        f"lags {p.get('lags')}; rolling windows {p.get('rolling_windows')}",
        f"- Stores: {lgbm.data.tags.get('stores')}",
    ]
    kaggle = cfg.paths.reports / "kaggle_score.json"
    if kaggle.exists():
        k = json.loads(kaggle.read_text(encoding="utf-8"))
        L += [
            "",
            "## Kaggle late submission",
            "",
            f"Private leaderboard score **{k['private']}** (public {k['public']}), submitted {k['date']}.",
            "The public score uses the known actuals for days 1914–1941 and is not meaningful.",
        ]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    out = PROJECT_ROOT / "RESULTS.md"
    out.write_text(build(cfg), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
