"""Derived signals over the stored daily series. Pure pandas, no Streamlit."""

from __future__ import annotations

import pandas as pd


def calendar_rolling_mean(
    df: pd.DataFrame,
    value_col: str,
    days: int = 7,
    date_col: str = "date",
) -> pd.Series:
    """Average observations in the trailing calendar window, preserving row order.

    Missing dates are not treated as zero. They simply contribute no
    observation, which is appropriate for device data that was not recorded.
    """
    if days < 1:
        raise ValueError("days must be positive")
    if df.empty:
        return pd.Series(index=df.index, dtype=float, name=f"{value_col}_ma{days}")

    work = pd.DataFrame(
        {
            "_date": pd.to_datetime(df[date_col]),
            "_value": df[value_col].to_numpy(),
            "_position": range(len(df)),
        }
    ).sort_values(["_date", "_position"])
    work["_mean"] = work.rolling(f"{days}D", on="_date", min_periods=1)["_value"].mean()
    values = work.sort_values("_position")["_mean"].to_numpy()
    return pd.Series(values, index=df.index, name=f"{value_col}_ma{days}")


def rolling_baseline_z(
    df: pd.DataFrame,
    value_col: str,
    *,
    window_days: int = 30,
    min_observations: int = 10,
    date_col: str = "date",
) -> pd.DataFrame:
    """Score each day against its own trailing calendar-window history.

    The window ends on the *previous* observation, so a day never contributes
    to the baseline it is scored against -- otherwise a large excursion damps
    its own z. Days with fewer than `min_observations` prior readings get NaN
    rather than a z computed from too little history, and a zero-variance
    history yields NaN rather than an infinite z.
    """
    work = df[[date_col, value_col]].dropna().sort_values(date_col).reset_index(drop=True)
    if work.empty:
        return pd.DataFrame(columns=[date_col, value_col, "baseline", "sd", "z"])

    dates = pd.to_datetime(work[date_col])
    values = work[value_col].to_numpy(dtype=float)
    baseline: list[float] = []
    sd: list[float] = []
    z: list[float] = []
    for position in range(len(work)):
        window_start = dates.iloc[position] - pd.Timedelta(days=window_days)
        in_window = ((dates < dates.iloc[position]) & (dates >= window_start)).to_numpy()
        prior = values[in_window]
        if len(prior) < min_observations:
            baseline.append(float("nan"))
            sd.append(float("nan"))
            z.append(float("nan"))
            continue
        mean = float(prior.mean())
        spread = float(prior.std(ddof=1))
        baseline.append(mean)
        sd.append(spread)
        z.append(float("nan") if spread == 0 else (values[position] - mean) / spread)

    out = work.copy()
    out["baseline"] = baseline
    out["sd"] = sd
    out["z"] = z
    return out


def lagged_correlation(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    *,
    lags: tuple[int, ...] = (0, 1, 2, 3),
    date_col: str = "date",
    min_pairs: int = 20,
) -> pd.DataFrame:
    """Spearman correlation between x on day d and y on day d+lag.

    Rank correlation rather than Pearson: these series are skewed and carry
    outlier days, and the question is monotone association, not linearity.
    Pairs are matched by calendar date, so a missing day drops its own pairs
    instead of silently shifting every later one.
    """
    work = df[[date_col, x_col, y_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col])
    rows = []
    for lag in lags:
        shifted = work[[date_col, y_col]].copy()
        shifted[date_col] = shifted[date_col] - pd.Timedelta(days=lag)
        merged = work[[date_col, x_col]].merge(shifted, on=date_col, how="inner").dropna()
        pairs = len(merged)
        rho = (
            merged[x_col].corr(merged[y_col], method="spearman")
            if pairs >= min_pairs
            else float("nan")
        )
        rows.append({"lag": lag, "n": pairs, "spearman": rho})
    return pd.DataFrame(rows)
