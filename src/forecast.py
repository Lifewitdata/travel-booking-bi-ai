"""Weekly realized-revenue forecast: holdout-scored, honest model choice.

Models compared on the last 8 complete weeks: 4-week moving average,
seasonal naive (same week last year, lag 52) and Holt-Winters
(trend + 52-week seasonality). The winner by MAE refits on all complete
weeks and forecasts the next 13 weeks (about 90 days).
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore")
HOLDOUT, HORIZON, SEASON = 8, 13, 52


def _hw(series, horizon):
    model = ExponentialSmoothing(series, trend="add", seasonal="add",
                                 seasonal_periods=SEASON,
                                 initialization_method="estimated").fit(optimized=True)
    return np.asarray(model.forecast(horizon), dtype=float)


def forecast_weekly(weekly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    w = weekly.sort_values("arrival_week").copy()
    series = w.groupby("arrival_week")["realized_revenue_eur"].sum().asfreq("W-MON")
    series = series.dropna()
    # First week starts Wed 2015-07-01 and last week ends Thu 2017-08-31,
    # so both edge weeks are partial. Drop them for forecasting.
    series = series.iloc[1:-1]
    train, test = series.iloc[:-HOLDOUT], series.iloc[-HOLDOUT:]
    ma4 = train.rolling(4).mean().iloc[-1]
    preds = {
        "moving_average_4w": np.repeat(ma4, HOLDOUT),
        "seasonal_naive_52w": series.iloc[-SEASON - HOLDOUT:-SEASON].to_numpy(),
        "holt_winters": _hw(train, HOLDOUT),
    }
    scores = pd.DataFrame([
        {"model": name, "mae_eur": float(np.mean(np.abs(test.to_numpy() - pred))),
         "rmse_eur": float(np.sqrt(np.mean((test.to_numpy() - pred) ** 2)))}
        for name, pred in preds.items()]).sort_values("mae_eur")
    winner = scores.iloc[0]["model"]
    if winner == "holt_winters":
        future = _hw(series, HORIZON)
    elif winner == "seasonal_naive_52w":
        future = series.iloc[-SEASON:-SEASON + HORIZON].to_numpy()
    else:
        future = np.repeat(series.rolling(4).mean().iloc[-1], HORIZON)
    future_idx = pd.date_range(series.index[-1] + pd.Timedelta(weeks=1),
                               periods=HORIZON, freq="W-MON")
    fc = pd.DataFrame({"arrival_week": future_idx, "forecast_model": winner,
                       "forecast_realized_revenue_eur": np.round(future, 2)})
    hist = pd.DataFrame({"arrival_week": series.index,
                         "actual_realized_revenue_eur": series.to_numpy()})
    return pd.concat([hist.assign(forecast_realized_revenue_eur=np.nan), fc],
                     ignore_index=True), scores
