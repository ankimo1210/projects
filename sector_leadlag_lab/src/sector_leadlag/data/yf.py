"""Daily prices from yfinance, kept as CSV in the snapshot store (design §4).

yfinance's ``history(auto_adjust=False, actions=True)`` gives OHLC and volume adjusted for
splits (not for dividends), the dividend-adjusted close, and the dividends and split ratios on
their ex-dates. Close times volume is therefore the traded value in yen or dollars.
"""

from __future__ import annotations

import io
import time as clock
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from .store import FetchError

US_SECTORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
COLUMNS = ("open", "high", "low", "close", "adj_close", "volume", "dividends", "splits")
RENAME = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
    "Dividends": "dividends",
    "Stock Splits": "splits",
}
ZONES = {"jp": ZoneInfo("Asia/Tokyo"), "us": ZoneInfo("America/New_York")}
COMPLETE_AFTER = time(18, 0)  # a day's bar is taken as final after 18:00 local time


def market_of(ticker: str) -> str:
    return "jp" if ticker.endswith(".T") else "us"


def complete_through(fetched_at: datetime, market: str) -> date:
    """The last local date whose daily bar was final when the data was fetched."""
    local = fetched_at.astimezone(ZONES[market])
    return local.date() if local.time() >= COMPLETE_AFTER else local.date() - timedelta(days=1)


def to_csv(history: pd.DataFrame, through: date) -> bytes:
    frame = history.rename(columns=RENAME)
    missing = [column for column in COLUMNS if column not in frame.columns]
    if missing:
        raise FetchError(f"the yfinance history lacks {missing}")
    frame = frame[list(COLUMNS)]
    index = pd.DatetimeIndex(frame.index)
    if index.tz is not None:
        index = index.tz_localize(None)  # keeps the exchange's local date
    frame = frame.set_axis(pd.DatetimeIndex(index.normalize(), name="date"))
    frame = frame[(frame.index <= pd.Timestamp(through)) & frame["close"].notna()]
    return frame.to_csv(float_format="%.10g").encode()


def _yfinance_history(ticker: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.Ticker(ticker).history(period="max", auto_adjust=False, actions=True)


def download(
    ticker: str,
    *,
    fetched_at: datetime | None = None,
    attempts: int = 4,
    history: Callable[[str], pd.DataFrame] = _yfinance_history,
    sleep: Callable[[float], None] = clock.sleep,
) -> bytes:
    """The full daily history of ``ticker`` as CSV bytes, without a day that was still trading."""
    stamp = fetched_at or datetime.now(UTC)
    last_error: Exception | None = None
    for attempt in range(attempts):
        frame = None
        try:
            frame = history(ticker)
        except Exception as error:  # yfinance raises several types when throttled
            last_error = error
        if frame is not None and not frame.empty:
            return to_csv(frame, complete_through(stamp, market_of(ticker)))
        if attempt + 1 < attempts:
            sleep(5.0 * 3**attempt)
    raise FetchError(f"yfinance returned no history for {ticker} ({last_error})")


def parse_csv(content: bytes) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(content), index_col="date", parse_dates=["date"])
    return frame.astype(float)
