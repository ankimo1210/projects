"""Fetch every raw input into the store: the listed-issues file and the yfinance histories (design §4).

The US sector ETFs and the Japanese sector ETFs must all download; a stock that fails is listed
and left out (the study reports how many TOPIX500 names have prices).
"""

from __future__ import annotations

import time as clock
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from . import jpx, yf
from .store import RAW_ROOT, FetchError, fetch, store_bytes


def snapshot_all(
    root: Path = RAW_ROOT,
    *,
    fetch_listing: Callable[[str], bytes] = fetch,
    download: Callable[..., bytes] = yf.download,
    pause: float = 0.3,
    sleep: Callable[[float], None] = clock.sleep,
    now: datetime | None = None,
) -> list[str]:
    lines: list[str] = []

    def keep(source: str, indicator: str, content: bytes, url: str, filename: str) -> None:
        result = store_bytes(root, source, indicator, content, url=url, filename=filename)
        state = "stored" if result.changed else "unchanged"
        lines.append(f"{source}/{indicator}: {state}, {result.size:,} bytes")

    content = fetch_listing(jpx.URL)
    listing = jpx.parse_listing(content)  # refuse a file in an unexpected layout before storing
    keep("jpx", "data_j", content, jpx.URL, "data_j.xlsx")
    fetched_at = now or datetime.now(UTC)
    required = [*yf.US_SECTORS, *jpx.ETF_TICKERS]
    stocks = [jpx.stock_ticker(code) for code in jpx.topix500(listing).index]
    for ticker in required + stocks:
        try:
            payload = download(ticker, fetched_at=fetched_at)
        except FetchError:
            if ticker in required:
                raise
            lines.append(f"yf/{ticker}: failed")
            continue
        keep("yf", ticker, payload, f"yfinance:{ticker}", f"{ticker}.csv")
        sleep(pause)
    return lines
