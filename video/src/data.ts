// Every number in the video comes from here: the project's own report files, the aggregates written by
// video/scripts/extract.py (public/data/m5.json, from the parquet files), or a cited README/config value.
import metricsJson from "../../reports/serving/metrics.json";
import kaggleJson from "../../reports/kaggle_score.json";
import monitoringJson from "../../reports/monitoring.json";
import m5Json from "../public/data/m5.json";

type ModelKey = "lgbm" | "seasonal_naive" | "moving_average_28";
type Summary = { per_fold: Record<string, number>; per_level_fold1: Record<string, number>; mean: number };

const metrics = metricsJson as unknown as {
  horizon: number;
  last_known_day: number;
  backtest_cutoffs: number[];
  summary: Record<ModelKey, Summary>;
};

export type Series = { history: number[]; pred: number[]; actual: number[] };
export const M5 = m5Json as unknown as {
  n_series: number;
  n_stores: number;
  n_states: number;
  states: string[];
  stores: string[];
  first_day: number;
  last_day: number;
  n_days: number;
  first_date: string;
  last_date: string;
  dates: Record<string, string>;
  levels: { level: string; n: number }[];
  n_level_series: number;
  hook: { n: number; weeks: number; lines: number[][] };
  total_daily: number[];
  fold: {
    cutoff: number;
    context_days: number;
    days: number[];
    total: Series & { abs_err_share: number };
    item: Series & { id: string; why: string };
  };
};

export const MODELS: { key: ModelKey; label: string; short: string }[] = [
  { key: "lgbm", label: "LightGBM, one model per store", short: "LightGBM" },
  { key: "seasonal_naive", label: "Seasonal naive (repeat last week)", short: "Seasonal naive" },
  { key: "moving_average_28", label: "Moving average (last 28 days)", short: "Moving avg 28" },
];

const S = metrics.summary;
export const HORIZON = metrics.horizon; // 28
export const LAST_DAY = metrics.last_known_day; // 1941
export const CUTOFFS = [...metrics.backtest_cutoffs].sort((a, b) => a - b); // 1857, 1885, 1913
export const LATEST_CUTOFF = Math.max(...metrics.backtest_cutoffs); // per_level_fold1 is this window

export const MEAN = { lgbm: S.lgbm.mean, seasonal_naive: S.seasonal_naive.mean, moving_average_28: S.moving_average_28.mean };
const bestBaseline = Math.min(MEAN.seasonal_naive, MEAN.moving_average_28);
/** Relative improvement over the best baseline: 1 - 0.7111 / 0.8938 = 20.4%. */
export const IMPROVEMENT = 1 - MEAN.lgbm / bestBaseline;
export const PER_FOLD = (cutoff: number) => ({
  lgbm: S.lgbm.per_fold[String(cutoff)],
  seasonal_naive: S.seasonal_naive.per_fold[String(cutoff)],
  moving_average_28: S.moving_average_28.per_fold[String(cutoff)],
});
export const FOLD_WINS = CUTOFFS.filter((c) => {
  const p = PER_FOLD(c);
  return p.lgbm < Math.min(p.seasonal_naive, p.moving_average_28);
}).length;

export const LEVEL_LABEL: Record<string, string> = {
  total: "Total",
  state: "State",
  store: "Store",
  category: "Category",
  department: "Department",
  state_category: "State × category",
  state_department: "State × department",
  store_category: "Store × category",
  store_department: "Store × department",
  item: "Item",
  item_state: "Item × state",
  item_store: "Item × store",
};

/** Per-level WRMSSE in the latest backtest window; a "win" = LightGBM below both baselines. */
export const LEVELS = Object.keys(S.lgbm.per_level_fold1).map((level) => {
  const lgbm = S.lgbm.per_level_fold1[level];
  const sn = S.seasonal_naive.per_level_fold1[level];
  const ma = S.moving_average_28.per_level_fold1[level];
  const base = sn <= ma ? { key: "seasonal_naive" as const, v: sn } : { key: "moving_average_28" as const, v: ma };
  return { level, label: LEVEL_LABEL[level] ?? level, lgbm, sn, ma, base, win: lgbm < Math.min(sn, ma) };
});
export const LEVEL_WINS = LEVELS.filter((l) => l.win).length;
export const LEVEL_LOSSES = LEVELS.filter((l) => !l.win);

const k = kaggleJson as { private: string; public: string; date: string };
export const KAGGLE = { private: k.private, date: k.date, firstDay: LAST_DAY + 1, lastDay: LAST_DAY + HORIZON };

const mon = monitoringJson as unknown as {
  window: { reference_days: number[]; current_days: number[] };
  drift: { sales_psi: number; price_psi: number };
  drift_alert: boolean;
  accuracy: { latest_cutoff: number; latest_wrmsse: number; relative_change: number };
  accuracy_alert: boolean;
  retrain_recommended: boolean;
};
export const MON = {
  salesPsi: mon.drift.sales_psi,
  pricePsi: mon.drift.price_psi,
  driftAlert: mon.drift_alert,
  change: mon.accuracy.relative_change,
  accuracyAlert: mon.accuracy_alert,
  retrain: mon.retrain_recommended,
  current: mon.window.current_days,
  reference: mon.window.reference_days,
};

// Cited from the repo (not in a JSON report):
// - thresholds: src/m5forecast/monitoring.py PSI_ALERT = 0.2, DECAY_ALERT = 0.10 (also MODEL_CARD.md)
// - model setup: RESULTS.md "Training setup" (from the MLflow run params) and configs/default.yaml
// - training time: README.md "took 92 minutes" (reports/train_log.txt: "done in 92.4 min")
// - training rows from day 1000: configs/default.yaml train_start_day, MODEL_CARD.md
export const CITED = {
  psiAlert: 0.2,
  decayAlert: 0.1,
  features: 35,
  lags: [28, 29, 30, 35, 42, 49, 56, 91, 364],
  windows: [7, 14, 28, 56, 112],
  tweediePower: 1.1,
  rounds: 1000,
  trainMinutes: 92,
  trainStartDay: 1000,
  backtestsPerStore: 3,
  repo: "github.com/Fares-Ayman-1/m5-demand-forecasting",
  kaggle: "kaggle.com/code/faresayman1/m5-leakage-safe-lightgbm-and-exact-wrmsse",
};
export const MODELS_TRAINED = M5.n_stores * (CITED.backtestsPerStore + 1); // 10 x (3 backtests + final)

export const fmt = (v: number, d = 4) => v.toFixed(d);
export const int = (v: number) => v.toLocaleString("en-US");
export const pct = (v: number, d = 1) => `${(v * 100).toFixed(d)}%`;
