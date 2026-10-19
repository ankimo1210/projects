"""Shared builders for the tests. Nothing here touches the network."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest
from sector_leadlag.data.jpx import COLUMNS, SECTORS


def _listing_bytes(rows: list[tuple[str, int, str]], stamp: str = "20260930") -> bytes:
    """A listed-issues workbook in the JPX layout; ``rows`` are (code, sector or 0, size)."""
    records = []
    for code, sector, size in rows:
        records.append(
            {
                "日付": stamp,
                "コード": code,
                "銘柄名": f"name {code}",
                "市場・商品区分": "プライム（内国株式）" if sector else "ETF・ETN",
                "33業種コード": "50" if sector else "-",
                "33業種区分": "水産・農林業" if sector else "-",
                "17業種コード": str(sector) if sector else "-",
                "17業種区分": SECTORS[sector - 1] if sector else "-",
                "規模コード": "1" if sector else "-",
                "規模区分": size if sector else "-",
            }
        )
    buffer = io.BytesIO()
    pd.DataFrame(records, columns=list(COLUMNS)).to_excel(buffer, index=False)
    return buffer.getvalue()


@pytest.fixture
def listing_bytes():
    return _listing_bytes


def _history(
    dates,
    *,
    open_,
    close,
    volume=None,
    dividends=None,
    splits=None,
    adj_close=None,
    tz: str = "Asia/Tokyo",
) -> pd.DataFrame:
    """A frame in the yfinance ``history(auto_adjust=False, actions=True)`` layout."""
    index = pd.DatetimeIndex(pd.to_datetime(list(dates))).tz_localize(tz)
    n = len(index)
    open_ = np.asarray(open_, dtype=float)
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close),
            "Low": np.minimum(open_, close),
            "Close": close,
            "Adj Close": close if adj_close is None else np.asarray(adj_close, dtype=float),
            "Volume": np.full(n, 1000.0) if volume is None else np.asarray(volume, dtype=float),
            "Dividends": np.zeros(n) if dividends is None else np.asarray(dividends, dtype=float),
            "Stock Splits": np.zeros(n) if splits is None else np.asarray(splits, dtype=float),
            "Capital Gains": np.zeros(n),
        },
        index=index,
    )


@pytest.fixture
def yf_history():
    return _history
