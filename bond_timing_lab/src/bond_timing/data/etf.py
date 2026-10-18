"""TLT, IEF and BIL total-return prices from yfinance (design §4.3; G0 and supplementary tables)."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from .store import RAW_ROOT, read_latest

TICKERS = ("TLT", "IEF", "BIL")
START = "2002-01-01"


def download_csv(ticker: str) -> bytes:
    """Dividend-adjusted daily closes as ``date,close`` CSV bytes."""
    import yfinance as yf

    frame = yf.download(
        ticker, start=START, auto_adjust=True, actions=False, progress=False, threads=False
    )
    close = frame["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    index = pd.DatetimeIndex(close.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    out = pd.DataFrame(
        {"close": close.to_numpy(dtype=float)}, index=pd.DatetimeIndex(index, name="date")
    )
    return out.to_csv(float_format="%.10g").encode()


def parse_prices(content: bytes) -> pd.Series:
    frame = pd.read_csv(io.BytesIO(content), index_col="date", parse_dates=["date"])
    return frame["close"].astype(float)


def monthly_total_returns(prices: pd.Series) -> pd.Series:
    """Month-end to month-end returns, without a final month that is still in progress."""
    month_end = prices.groupby(prices.index.to_period("M")).last()
    last = prices.index[-1]
    if last != pd.offsets.BMonthEnd().rollforward(last):
        month_end = month_end.iloc[:-1]
    return (month_end / month_end.shift(1) - 1.0).iloc[1:]


def daily_returns(prices: pd.Series) -> pd.Series:
    return (prices / prices.shift(1) - 1.0).iloc[1:]


def load_prices(ticker: str, root: Path = RAW_ROOT) -> pd.Series:
    return parse_prices(read_latest(root, "etf", ticker))
