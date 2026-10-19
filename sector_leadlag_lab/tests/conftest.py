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


def _panel(open_, close, *, volume=None, dividends=None, splits=None, adj_close=None, sector=None):
    """A ``baskets.Panel`` from frames that share an index and columns."""
    from sector_leadlag.baskets import Panel

    zeros = close * 0.0
    return Panel(
        open=open_,
        close=close,
        adj_close=close if adj_close is None else adj_close,
        volume=zeros + 1000.0 if volume is None else volume,
        dividends=zeros if dividends is None else dividends,
        splits=zeros if splits is None else splits,
        sector=pd.Series(1, index=close.columns) if sector is None else sector,
    )


@pytest.fixture
def make_panel():
    return _panel


def _world(*, seed: int = 0, etf_lead=(1.0, -1.0), stock_lead=(1.0, 1.0), names: int = 2):
    """A study on synthetic prices, 2009-06 to 2026-10.

    The close-to-close returns carry no lead, so the signal (built from them alone) is known
    before the opens are made. Each open is then set so that the open-to-close return is
    lead x 0.002 x sz + noise: the first value of ``etf_lead`` and ``stock_lead`` before
    本番 B, the second from B on.
    """
    from dataclasses import replace
    from datetime import date

    from sector_leadlag.baskets import SECTORS, Panel
    from sector_leadlag.data.jpx import Listing
    from sector_leadlag.data.yf import US_SECTORS
    from sector_leadlag.signal import cross_standardize
    from sector_leadlag.stages import build_signal
    from sector_leadlag.study import B, Study
    from sector_leadlag.timing import last_us_before

    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2009-06-01", "2026-10-16")
    jp_days = pd.DatetimeIndex(days[rng.random(len(days)) > 0.04], name="date")
    us_days = pd.DatetimeIndex(days[rng.random(len(days)) > 0.04], name="date")
    us_ret = 1 + 0.01 * rng.normal(size=(len(us_days), 11))
    us = pd.DataFrame(100 * np.cumprod(us_ret, axis=0), index=us_days, columns=list(US_SECTORS))
    us.loc[:"2015-10-07", "XLRE"] = np.nan
    us.loc[:"2018-06-18", "XLC"] = np.nan
    market = 0.008 * rng.normal(size=(len(jp_days), 1))
    etf_c2c = market + 0.006 * rng.normal(size=(len(jp_days), 17))
    etf_close = pd.DataFrame(
        1000 * np.cumprod(1 + etf_c2c, axis=0), index=jp_days, columns=list(SECTORS)
    )
    codes = [f"{1000 + 10 * k + i}" for k in SECTORS for i in range(names)]
    sector = pd.Series([k for k in SECTORS for _ in range(names)], index=codes)
    noise = 0.01 * rng.normal(size=(len(jp_days), len(codes)))
    stock_c2c = etf_c2c[:, sector.to_numpy() - 1] + noise
    start = rng.uniform(500, 2500, size=len(codes))
    stock_close = pd.DataFrame(
        start * np.cumprod(1 + stock_c2c, axis=0), index=jp_days, columns=codes
    )

    def panel(close: pd.DataFrame, codes_sector: pd.Series, zero_share: float) -> Panel:
        volume = pd.DataFrame(
            rng.uniform(1e4, 1e5, size=close.shape), index=close.index, columns=close.columns
        )
        volume = volume.mask(rng.random(close.shape) < zero_share, 0.0)
        zeros = close * 0.0
        return Panel(close.copy(), close, close.copy(), volume, zeros, zeros, codes_sector)

    listing = Listing(
        date(2026, 9, 30),
        pd.DataFrame(
            {"name": codes, "sector": sector.to_numpy(), "size": "TOPIX Mid400"},
            index=pd.Index(codes, name="code"),
        ),
    )
    etf_sector = pd.Series(list(SECTORS), index=list(SECTORS))
    study = Study(
        listing,
        us,
        us_days,
        jp_days,
        last_us_before(jp_days, us_days),
        panel(etf_close, etf_sector, 0.05),
        panel(stock_close, sector, 0.01),
        (),
    )
    sz = cross_standardize(build_signal(study, "lagged")).reindex(jp_days).to_numpy()
    in_b = (jp_days >= B[0])[:, None]

    def opened(p: Panel, lead, column_sector: np.ndarray) -> Panel:
        size = 0.002 * np.where(in_b, lead[1], lead[0])
        o2c = np.nan_to_num(size * sz[:, column_sector - 1]) + 0.004 * rng.normal(
            size=p.close.shape
        )
        return replace(p, open=p.close / (1 + o2c))

    return replace(
        study,
        etf=opened(study.etf, etf_lead, np.arange(1, 18)),
        stocks=opened(study.stocks, stock_lead, sector.to_numpy()),
    )


@pytest.fixture(scope="session")
def decayed_world():
    """The lead is real in the stocks; in the ETFs it turns negative from 本番 B on."""
    return _world()


@pytest.fixture(scope="session")
def etf_only_world():
    """The lead is in the ETFs only."""
    return _world(seed=1, stock_lead=(0.0, 0.0))
