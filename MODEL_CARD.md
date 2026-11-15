# Model card: M5 per-store LightGBM forecaster

## What it does
It predicts daily unit sales for each Walmart item in each store, 1 to 28 days ahead, from sales
history, prices, calendar events and SNAP days. There is one LightGBM model per store (10 models).

## Intended use
- A portfolio demonstration of a retail demand-forecasting system, and a starting point for
  inventory planning prototypes.
- **Not** for production ordering decisions without retraining on the operator's own data and
  checking the costs of under- and over-forecasting.

## Training data
M5 Forecasting – Accuracy (Kaggle, Walmart via the University of Nicosia):
- 30,490 bottom-level series in 10 stores across 3 US states (CA, TX, WI).
- Days 1–1941 (2011-01-29 to 2016-05-22).
- Training rows use days 1000 onward; features use all history.

Data use follows the competition rules. The data is not redistributed.

## Evaluation
- **Metric:** WRMSSE, the official metric. It averages 12 aggregation levels (from total sales down to
  item × store), each series weighted by its dollar sales.
- **Validation:** three rolling 28-day backtests (cutoffs at days 1913, 1885 and 1857).
- **Comparison:** a seasonal-naive baseline and a 28-day moving-average baseline.
- **Results:** in [RESULTS.md](RESULTS.md), generated from MLflow.

## Known limitations
- **Long-history features only:** sales features use lags of 28 days or more, so the model reacts
  slowly to sudden changes inside the forecast window.
- **Point forecasts only:** no prediction intervals. The M5 Uncertainty track is not covered.
- **Short history:** items with very short history get little item-specific signal.
- **Not reconciled:** forecasts are made at the bottom level only, then summed.
- **Possible bias:** stores or departments with sparse sales may be systematically over- or
  under-forecast. Error by level is reported in RESULTS.md.

## Monitoring
`python -m m5forecast.monitoring` compares the latest 28 days with the 28 days before them.
- **Sales and price drift:** a PSI above 0.2 raises an alert.
- **Accuracy decay:** WRMSSE rising more than 10% across backtests raises an alert.
- **Retraining:** either alert sets `retrain_recommended`.
