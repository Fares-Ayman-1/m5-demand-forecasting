"""Drift and accuracy monitoring with a retrain trigger.

Two checks, run after each data refresh:
1. Input drift: Population Stability Index (PSI) of daily unit sales and of sell prices, comparing the
   latest 28 days with the 28 days before them. PSI > 0.2 is the usual "significant shift" threshold.
2. Accuracy decay: WRMSSE of the most recent backtest versus the mean of the earlier ones. An increase
   of more than 10% means the model is ageing.

Either alarm sets ``retrain_recommended``. The report is written to reports/monitoring.{json,md}.

    uv run python -m m5forecast.monitoring
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from typing import Any

import numpy as np
import polars as pl

from m5forecast.config import Config, load_config
from m5forecast.data.wide import WideData

PSI_ALERT = 0.2
DECAY_ALERT = 0.10


def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """PSI over quantile bins of the reference distribution (handles heavy zero inflation)."""
    reference, current = reference[np.isfinite(reference)], current[np.isfinite(current)]
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if edges.size < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref = np.histogram(reference, edges)[0] / reference.size
    cur = np.histogram(current, edges)[0] / current.size
    eps = 1e-6
    ref, cur = np.clip(ref, eps, None), np.clip(cur, eps, None)
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def check(cfg: Config, wide: WideData, fold_scores: dict[int, float] | None = None) -> dict[str, Any]:
    h, last = cfg.horizon, cfg.last_day
    cur = wide.window(last - h + 1, h).astype(float).ravel()
    ref = wide.window(last - 2 * h + 1, h).astype(float).ravel()

    prices = wide.prices.join(wide.calendar.select("wm_yr_wk", "d"), on="wm_yr_wk")
    p_cur = prices.filter(pl.col("d").is_between(last - h + 1, last))["sell_price"].to_numpy()
    p_ref = prices.filter(pl.col("d").is_between(last - 2 * h + 1, last - h))["sell_price"].to_numpy()

    drift = {"sales_psi": psi(ref, cur), "price_psi": psi(p_ref, p_cur)}
    out: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "window": {"reference_days": [last - 2 * h + 1, last - h], "current_days": [last - h + 1, last]},
        "drift": drift,
        "drift_alert": any(v > PSI_ALERT for v in drift.values()),
    }
    if fold_scores and len(fold_scores) >= 2:
        latest = max(fold_scores)
        earlier = [v for k, v in fold_scores.items() if k != latest]
        decay = fold_scores[latest] / float(np.mean(earlier)) - 1
        out["accuracy"] = {
            "latest_cutoff": latest,
            "latest_wrmsse": fold_scores[latest],
            "relative_change": decay,
        }
        out["accuracy_alert"] = decay > DECAY_ALERT
    out["retrain_recommended"] = bool(out["drift_alert"] or out.get("accuracy_alert", False))
    return out


def to_markdown(r: dict[str, Any]) -> str:
    L = [
        "# Monitoring report",
        "",
        f"Checked {r['checked_at']}. Reference days {r['window']['reference_days']}, "
        f"current days {r['window']['current_days']}.",
        "",
        "| Check | Value | Threshold | Alert |",
        "|---|---:|---:|---|",
    ]
    for k, v in r["drift"].items():
        L.append(f"| {k.replace('_', ' ')} | {v:.4f} | {PSI_ALERT} | {'yes' if v > PSI_ALERT else 'no'} |")
    if "accuracy" in r:
        a = r["accuracy"]
        L.append(
            f"| WRMSSE change, latest backtest vs earlier | {a['relative_change']:+.1%} "
            f"| +{DECAY_ALERT:.0%} | {'yes' if r['accuracy_alert'] else 'no'} |"
        )
    L += ["", f"**Retrain recommended: {'yes' if r['retrain_recommended'] else 'no'}**"]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    cfg = load_config(ap.parse_args().config)
    wide = WideData.load(cfg.paths.interim)
    metrics = cfg.paths.reports / "serving" / "metrics.json"
    folds = None
    if metrics.exists():
        m = json.loads(metrics.read_text(encoding="utf-8"))
        folds = {int(k): float(v) for k, v in m["summary"]["lgbm"]["per_fold"].items()}
    r = check(cfg, wide, folds)
    (cfg.paths.reports / "monitoring.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    (cfg.paths.reports / "monitoring.md").write_text(to_markdown(r), encoding="utf-8")
    print(to_markdown(r))


if __name__ == "__main__":
    main()
