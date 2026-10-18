"""FRED series through the keyless CSV endpoint (design §4.2).

DTB3 is the 3-month bill on a discount basis (daily). The month-end value of month t sets
the cash return of month t+1. TB3MS is stored as a backup but never fills DTB3 gaps.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

from .store import RAW_ROOT, read_latest

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
SERIES = ("DTB3", "TB3MS")


def parse_fred_csv(content: bytes) -> pd.Series:
    frame = pd.read_csv(io.BytesIO(content), na_values=[".", ""])
    name = frame.columns[1]
    values = pd.to_numeric(frame[name], errors="coerce").to_numpy(dtype=float)
    return pd.Series(values, index=pd.DatetimeIndex(pd.to_datetime(frame.iloc[:, 0])), name=name)


def month_end_last(series: pd.Series) -> pd.Series:
    """Last valid daily value of each calendar month (a holiday month-end takes an earlier day)."""
    valid = series.dropna()
    out = valid.groupby(valid.index.to_period("M")).last()
    return out.reindex(pd.period_range(out.index[0], out.index[-1], freq="M"))


def missing_months(month_end: pd.Series) -> list[str]:
    return [str(month) for month in month_end.index[month_end.isna()]]


def bill_bey(discount_pct: pd.Series) -> pd.Series:
    """Bond-equivalent yield (decimal) of a 91-day bill quoted on a discount basis."""
    d = discount_pct / 100.0
    return 365.0 * d / (360.0 - 91.0 * d)


def bey_to_cc(bey: pd.Series) -> pd.Series:
    """Continuously compounded annual rate equivalent to a 91-day bond-equivalent yield."""
    return np.log1p(bey * 91.0 / 365.0) * 365.0 / 91.0


def cash_returns(bey: pd.Series) -> pd.Series:
    """Simple cash return of return month p: the bill yield at the end of p-1, over 12."""
    return (bey / 12.0).shift(1)


def load_dtb3_bey(root: Path = RAW_ROOT) -> pd.Series:
    return bill_bey(month_end_last(parse_fred_csv(read_latest(root, "fred", "DTB3"))))
