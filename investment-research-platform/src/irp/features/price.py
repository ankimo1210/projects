"""Price-based features — all strictly *causal* (no look-ahead).

Every function here computes feature[t] from information available at or before
``t`` only: rolling windows are trailing, ``pct_change`` never forward-fills, and
cross-sectional transforms use a single date's cross-section. The invariant is
tested directly (``tests/test_features.py`` appends future rows and asserts the
earlier outputs are unchanged).

Two shapes are supported:
  * a single asset  -> ``pd.Series`` indexed by a DatetimeIndex
  * a panel         -> ``pd.DataFrame`` (rows = dates, columns = assets)

Rolling functions operate column-wise, so they accept either shape. The
cross-sectional helpers (``cross_sectional_*``) only make sense on a panel.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def returns(price: pd.Series | pd.DataFrame, periods: int = 1, *, log: bool = False):
    """Simple or log return over ``periods`` bars.

    ``fill_method=None`` is explicit: a gap (NaN) is never forward-filled before
    differencing — a missing price yields a missing return, by design.
    """
    if log:
        return np.log(price).diff(periods)
    return price.pct_change(periods, fill_method=None)


def cumulative_return(price: pd.Series | pd.DataFrame, window: int):
    """Trailing total return over ``window`` bars: price[t] / price[t-window] - 1."""
    return price / price.shift(window) - 1.0


def momentum(price: pd.Series | pd.DataFrame, lookback: int = TRADING_DAYS, skip: int = 21):
    """Classic ``lookback``-minus-``skip`` momentum (e.g. 12-1).

    Return from ``t-lookback`` to ``t-skip`` — the most recent ``skip`` bars are
    excluded to avoid short-term reversal. Uses only past prices, so it is causal.
    """
    if skip < 0 or lookback <= skip:
        raise ValueError("require 0 <= skip < lookback")
    past = price.shift(skip)
    return past / price.shift(lookback) - 1.0


def moving_average(price: pd.Series | pd.DataFrame, window: int, *, min_periods: int | None = None):
    """Trailing simple moving average."""
    return price.rolling(window, min_periods=min_periods or window).mean()


def ma_ratio(price: pd.Series | pd.DataFrame, window: int):
    """Price relative to its trailing moving average minus 1 (a trend gauge)."""
    return price / moving_average(price, window) - 1.0


def rolling_volatility(
    rets: pd.Series | pd.DataFrame,
    window: int,
    *,
    annualize: bool = False,
    periods_per_year: int = TRADING_DAYS,
):
    """Trailing standard deviation of returns (optionally annualized)."""
    vol = rets.rolling(window, min_periods=window).std()
    return vol * np.sqrt(periods_per_year) if annualize else vol


def realized_volatility(
    price: pd.Series | pd.DataFrame,
    window: int,
    *,
    annualize: bool = True,
    periods_per_year: int = TRADING_DAYS,
):
    """Trailing realized volatility from log returns."""
    return rolling_volatility(
        returns(price, log=True),
        window,
        annualize=annualize,
        periods_per_year=periods_per_year,
    )


def ewma_volatility(rets: pd.Series | pd.DataFrame, halflife: float):
    """Exponentially-weighted volatility (EWM is backward-looking, so causal)."""
    return rets.ewm(halflife=halflife, min_periods=1).std()


def rolling_zscore(
    series: pd.Series | pd.DataFrame, window: int, *, min_periods: int | None = None
):
    """Trailing z-score: (x - rolling_mean) / rolling_std over a *trailing* window.

    Deliberately NOT a full-sample z-score, which would leak future statistics
    into earlier dates.
    """
    mp = min_periods or window
    mean = series.rolling(window, min_periods=mp).mean()
    std = series.rolling(window, min_periods=mp).std()
    return (series - mean) / std.replace(0.0, np.nan)


def drawdown(price: pd.Series | pd.DataFrame):
    """Current drawdown from the trailing running peak: price/cummax - 1 (<= 0).

    ``cummax`` is an expanding (trailing) operation, so each point uses only past
    and present prices.
    """
    return price / price.cummax() - 1.0


def rsi(price: pd.Series, window: int = 14):
    """Wilder's RSI (single asset). Trailing EWM of gains/losses, so causal."""
    delta = price.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


# --- cross-sectional (panel only): each date's row is transformed on its own ---
def cross_sectional_zscore(panel: pd.DataFrame, *, min_count: int = 3) -> pd.DataFrame:
    """Per-date z-score across assets (mean 0, unit std within each row).

    Uses only the values observed on that date, so it introduces no time-axis
    look-ahead. Rows with fewer than ``min_count`` valid assets become NaN.
    """
    mean = panel.mean(axis=1)
    std = panel.std(axis=1).replace(0.0, np.nan)
    z = panel.sub(mean, axis=0).div(std, axis=0)
    enough = panel.notna().sum(axis=1) >= min_count
    return z.where(enough, other=np.nan)


def cross_sectional_rank(panel: pd.DataFrame, *, pct: bool = True) -> pd.DataFrame:
    """Per-date cross-asset rank (percentile in [0, 1] when ``pct``)."""
    return panel.rank(axis=1, pct=pct)
