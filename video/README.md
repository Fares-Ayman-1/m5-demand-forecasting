# Project video: M5 Demand Forecasting (Walmart), week 4 of 4

A 92-second explainer built with [Remotion](https://www.remotion.dev/) and the shared light-theme kit
(`src/kit/`, see `D:\ml-portfolio\_video-kit\README.md`). Every number on screen comes from one of three
places, all wired up in `src/data.ts`:

- the project's own reports: `reports/serving/metrics.json`, `reports/kaggle_score.json`,
  `reports/monitoring.json` (imported directly);
- aggregates computed from the parquet files by `scripts/extract.py` (`public/data/m5.json`);
- a few setup values cited from `README.md`, `RESULTS.md`, `configs/default.yaml` and
  `src/m5forecast/monitoring.py` (listed in the `CITED` block of `src/data.ts`).

| Output | Size | Use |
|---|---|---|
| `out/m5-wide.mp4` | 1920 × 1080 | YouTube, GitHub README, portfolio site |
| `out/m5-square.mp4` | 1080 × 1080 | LinkedIn feed |

## Rebuild

Run from the project root unless noted. The video needs `data/interim/` (from
`python -m m5forecast.data.prepare`) and `reports/` (from `python -m m5forecast.train`).

```bash
# 1. aggregates for the charts -> video/public/data/m5.json (lazy polars scans, ~125 KB out)
UV_CACHE_DIR=D:/uv-cache uv run --no-sync python video/scripts/extract.py

# 2. screen recording of the real dashboard -> video/public/demo.mp4
UV_CACHE_DIR=D:/uv-cache uv run --no-sync streamlit run app/dashboard.py --server.port 8501 --server.headless true &
cd video
node scripts/capture.mjs capture/plan.json            # -> capture/demo.webm (2560 x 1600, ~22 s)
ffmpeg -i capture/demo.webm -vf "fps=30,format=yuv420p" -c:v libx264 -crf 14 public/demo.mp4
# then stop the server: netstat -ano | findstr :8501 ; taskkill //PID <pid> //F
cd ..

# 3. original music bed + sound effects, timed to scenes.json -> video/public/music.mp3, sfx.mp3
.venv/Scripts/python video/scripts/music.py --root E --mode minor --bpm 100

# 4. preview, review stills, render
cd video
npm install
npm run studio
node scripts/stills.mjs Wide 155 325 505      # -> out/stills/ (one process at a time)
npm run render:wide                           # -> out/m5-wide.mp4
npm run render:square                         # -> out/m5-square.mp4
```

`capture/plan.json` picks store CA_3, department FOODS_3 and item FOODS_3_090 in the series explorer,
scrolls to the most recent backtest, then opens the "Error by level" tab. The demo scene plays the
recording from 1 s at 1.75× (`DEMO_START`, `DEMO_RATE` in `src/scenes/App.tsx`). If `public/demo.mp4`
is missing the scene shows a placeholder.

`public/data/`, `public/demo.mp4` and `capture/` are derived from the competition data, so they are
git-ignored.

## Scenes

`scenes.json` is the single source of truth for order, duration (frames at 30 fps, 10-frame
cross-fades) and music cues; `music.py` reads it too. Change a duration there and re-run `music.py`.

| # | Key | Frames | What |
|---|---|---:|---|
| 1 | `title` | 180 | 70 store × department weekly sales lines + "Week 4 of 4" title |
| 2 | `problem` | 180 | 30,490 series, 10 stores, 3 states, 1,941 days; total daily sales and the 28 days to forecast |
| 3 | `hierarchy` | 190 | the 12 WRMSSE levels and their series counts (42,840 in total) |
| 4 | `leakage` | 200 | lags and rolling windows all end at t − 28; the leakage test |
| 5 | `model` | 180 | one LightGBM per store, Tweedie, 35 features, 92 minutes on a laptop CPU |
| 6 | `backtests` | 165 | three rolling-origin backtests (cutoffs 1857, 1885, 1913) and the hidden Kaggle window |
| 7 | `results` | 250 | mean WRMSSE vs two baselines (20.4% lower), per-window table |
| 8 | `levels` | 250 | per-level WRMSSE in the latest window: best at 10 of 12 levels |
| 9 | `forecast` | 240 | forecast vs actual: total of all series, and FOODS_3_090 at CA_3 |
| 10 | `kaggle` | 135 | private leaderboard 0.59184 on days 1942–1969 |
| 11 | `monitoring` | 210 | PSI drift tiny, error +16.1%, retrain recommended |
| 12 | `demo` | 360 | the real Streamlit dashboard in a browser frame |
| 13 | `engineering` | 150 | FastAPI, Docker, CI, MLflow, tests, monitoring |
| 14 | `outro` | 210 | name, links, scope line, data credit, all four weeks |
