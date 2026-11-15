# Results

Generated from MLflow on 2026-11-15 17:32 UTC by `python -m m5forecast.report`.
Metric: **WRMSSE** (the official M5 Accuracy metric; lower is better), on 3 rolling 28-day backtests over every series of the stores listed below.
Every number below is a logged MLflow metric of the run shown.

| Model | days 1914–1941 | days 1886–1913 | days 1858–1885 | Mean | MLflow run |
|---|---:|---:|---:|---:|---|
| LightGBM, Tweedie, one model per store | 0.7835 | 0.5950 | 0.7548 | **0.7111** | `43ba469bf8174173875c076004f08071` |
| Seasonal naive (repeat last week) | 0.8697 | 0.9228 | 0.8889 | **0.8938** | `36d34514a6684172a25dd6a1ade26d67` |
| Moving average (last 28 days) | 1.0823 | 1.0975 | 1.0500 | **1.0766** | `36d34514a6684172a25dd6a1ade26d67` |

LightGBM lowers mean WRMSSE by **20.4%** relative to the best baseline.

## WRMSSE by aggregation level (backtest days 1914–1941)

| Level | LightGBM |
|---|---:|
| total | 0.7926 |
| state | 0.7635 |
| store | 0.7687 |
| category | 0.7600 |
| department | 0.7538 |
| state × category | 0.7439 |
| state × department | 0.7440 |
| store × category | 0.7588 |
| store × department | 0.7740 |
| item | 0.8516 |
| item × state | 0.8473 |
| item × store | 0.8443 |

## Training setup (from the run's parameters)

- Boosting rounds: 1000; learning rate 0.05; leaves 255; Tweedie power 1.1
- Training rows from day 1000; 35 features; lags [28, 29, 30, 35, 42, 49, 56, 91, 364]; rolling windows [7, 14, 28, 56, 112]
- Stores: CA_1,CA_2,CA_3,CA_4,TX_1,TX_2,TX_3,WI_1,WI_2,WI_3

## Kaggle late submission

Private leaderboard score **0.59184** (public 0.00000), submitted 2026-11-15.
The public score uses the known actuals for days 1914–1941 and is not meaningful.
