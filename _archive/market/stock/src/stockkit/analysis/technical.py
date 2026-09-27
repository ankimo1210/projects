"""Technical indicators.

All functions take a price DataFrame (with at least a 'close' column) or a
Series and return a Series/DataFrame indexed identically.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _close(x: pd.DataFrame | pd.Series) -> pd.Series:
    if isinstance(x, pd.Series):
        return x
    if "adj_close" in x.columns:
        return x["adj_close"]
    return x["close"]


def sma(x: pd.DataFrame | pd.Series, window: int = 20) -> pd.Series:
    return _close(x).rolling(window=window, min_periods=window).mean()


def ema(x: pd.DataFrame | pd.Series, window: int = 20) -> pd.Series:
    return _close(x).ewm(span=window, adjust=False).mean()


def rsi(x: pd.DataFrame | pd.Series, window: int = 14) -> pd.Series:
    s = _close(x)
    delta = s.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd(
    x: pd.DataFrame | pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    s = _close(x)
    macd_line = s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()
    sig = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({"macd": macd_line, "signal": sig, "hist": macd_line - sig})


def bollinger(x: pd.DataFrame | pd.Series, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    s = _close(x)
    mid = s.rolling(window).mean()
    std = s.rolling(window).std()
    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std})


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / window, adjust=False).mean()


def returns(x: pd.DataFrame | pd.Series, log: bool = False) -> pd.Series:
    s = _close(x)
    return np.log(s / s.shift(1)) if log else s.pct_change()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience: append common indicators to a price DataFrame."""
    out = df.copy()
    out["sma20"] = sma(df, 20)
    out["sma50"] = sma(df, 50)
    out["sma200"] = sma(df, 200)
    out["ema20"] = ema(df, 20)
    out["rsi14"] = rsi(df, 14)
    m = macd(df)
    out[["macd", "macd_signal", "macd_hist"]] = m[["macd", "signal", "hist"]]
    bb = bollinger(df)
    out[["bb_mid", "bb_upper", "bb_lower"]] = bb[["mid", "upper", "lower"]]
    if {"high", "low", "close"}.issubset(df.columns):
        out["atr14"] = atr(df, 14)
    return out


def signal_golden_cross(df: pd.DataFrame, fast: int = 50, slow: int = 200) -> pd.Series:
    """+1 when fast crosses above slow, -1 on death cross, 0 otherwise."""
    f = sma(df, fast)
    s = sma(df, slow)
    diff = (f > s).astype(int).diff()
    return diff.fillna(0).astype(int)
