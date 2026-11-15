"""Streamlit dashboard over the serving bundle and the backtests.

uv run streamlit run app/dashboard.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import plotly.graph_objects as go
import polars as pl
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SERVING = Path(os.environ.get("SERVING_DIR", ROOT / "reports" / "serving"))
BACKTEST = Path(os.environ.get("BACKTEST_DIR", ROOT / "reports" / "backtest"))

GOLD, BLUE, GREY = "#c99a3f", "#4f78e0", "#8a8f99"

st.set_page_config(page_title="M5 demand forecasting", layout="wide")


@st.cache_data
def load() -> tuple[pl.DataFrame, pl.DataFrame, dict, pl.DataFrame | None]:
    fc = pl.read_parquet(SERVING / "forecast.parquet")
    hist = pl.read_parquet(SERVING / "history.parquet")
    metrics = json.loads((SERVING / "metrics.json").read_text(encoding="utf-8"))
    folds = sorted(BACKTEST.glob("fold_*.parquet"))
    bt = pl.read_parquet(folds[-1]) if folds else None  # most recent backtest window
    return fc, hist, metrics, bt


if not (SERVING / "forecast.parquet").exists():
    st.error("No serving bundle found. Run `python -m m5forecast.train` first.")
    st.stop()

fc, hist, metrics, bt = load()
summary = metrics["summary"]

st.title("M5 demand forecasting")
st.caption(
    f"LightGBM (Tweedie), one model per store · trained {metrics['trained_at']} · "
    f"forecasting days {metrics['last_known_day'] + 1}–{metrics['last_known_day'] + metrics['horizon']}"
)

cols = st.columns(3)
labels = {"lgbm": "LightGBM", "seasonal_naive": "Seasonal naive", "moving_average_28": "Moving average 28"}
for col, key in zip(cols, labels, strict=True):
    delta = None
    if key == "lgbm":
        best = min(summary[k]["mean"] for k in labels if k != "lgbm")
        delta = f"{summary['lgbm']['mean'] / best - 1:+.1%} vs best baseline"
    col.metric(f"{labels[key]} · mean WRMSSE", f"{summary[key]['mean']:.4f}", delta, delta_color="inverse")

tab_series, tab_levels = st.tabs(["Series explorer", "Error by level"])

with tab_series:
    c1, c2, c3 = st.columns(3)
    store = c1.selectbox("Store", sorted(fc["store_id"].unique().to_list()))
    dept = c2.selectbox(
        "Department", sorted(fc.filter(pl.col("store_id") == store)["dept_id"].unique().to_list())
    )
    items = sorted(
        fc.filter((pl.col("store_id") == store) & (pl.col("dept_id") == dept))["item_id"].unique().to_list()
    )
    item = c3.selectbox("Item", ["(whole department)", *items])

    def pick(df: pl.DataFrame) -> pl.DataFrame:
        df = df.filter(pl.col("id").str.contains(f"_{store}_"))
        if item == "(whole department)":
            return df.filter(pl.col("id").str.starts_with(dept + "_"))
        return df.filter(pl.col("id").str.starts_with(f"{item}_{store}"))

    h = pick(hist).group_by("date").agg(pl.col("sales").sum()).sort("date").tail(180)
    f = pick(fc).group_by("date").agg(pl.col("forecast").sum()).sort("date")
    fig = go.Figure()
    fig.add_scatter(x=h["date"], y=h["sales"], name="Actual", line={"color": GREY})
    fig.add_scatter(x=f["date"], y=f["forecast"], name="Forecast", line={"color": GOLD, "width": 3})
    fig.update_layout(
        height=380,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        yaxis_title="Units per day",
        legend={"orientation": "h"},
    )
    st.plotly_chart(fig, use_container_width=True)

    if bt is not None:
        b = (
            pick(bt.join(hist.select("d", "date").unique("d"), on="d", how="left"))
            .group_by("d")
            .agg(pl.col("pred").sum(), pl.col("actual").sum())
            .sort("d")
        )
        st.subheader(f"Most recent backtest: days {b['d'].min()}–{b['d'].max()}")
        fig2 = go.Figure()
        fig2.add_scatter(x=b["d"], y=b["actual"], name="Actual", line={"color": GREY})
        fig2.add_scatter(
            x=b["d"], y=b["pred"], name="Forecast made at the cutoff", line={"color": BLUE, "width": 3}
        )
        fig2.update_layout(
            height=320,
            margin={"l": 10, "r": 10, "t": 30, "b": 10},
            xaxis_title="M5 day",
            yaxis_title="Units per day",
            legend={"orientation": "h"},
        )
        st.plotly_chart(fig2, use_container_width=True)

with tab_levels:
    lv = summary["lgbm"]["per_level_fold1"]
    base = summary["seasonal_naive"]["per_level_fold1"]
    names = list(lv)
    fig3 = go.Figure()
    fig3.add_bar(
        y=[n.replace("_", " × ") for n in names],
        x=[base[n] for n in names],
        name="Seasonal naive",
        orientation="h",
        marker_color=GREY,
    )
    fig3.add_bar(
        y=[n.replace("_", " × ") for n in names],
        x=[lv[n] for n in names],
        name="LightGBM",
        orientation="h",
        marker_color=GOLD,
    )
    fig3.update_layout(
        barmode="group",
        height=520,
        xaxis_title="WRMSSE (lower is better)",
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        legend={"orientation": "h"},
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption(
        f"Backtest window after cutoff day {metrics['backtest_cutoffs'][0]}. "
        f"MLflow runs: {metrics['mlflow_run_ids']}"
    )
