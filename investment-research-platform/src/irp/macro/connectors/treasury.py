"""US Treasury daily par yield curve (free, no key) from treasury.gov.

Indicator is a tenor: one of TENORS keys (e.g. ``"10y"``, ``"2y"``, ``"3m"``).
Yields are released end-of-day, so ``release_date == period`` (vintage exact).
"""

from __future__ import annotations

import io

import pandas as pd
import requests

from ..base import MacroConnector
from ..schema import MacroObservation

TENORS = {
    "1m": "1 Mo",
    "3m": "3 Mo",
    "6m": "6 Mo",
    "1y": "1 Yr",
    "2y": "2 Yr",
    "3y": "3 Yr",
    "5y": "5 Yr",
    "7y": "7 Yr",
    "10y": "10 Yr",
    "20y": "20 Yr",
    "30y": "30 Yr",
}
BASE = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all"
)


class TreasuryConnector(MacroConnector):
    source = "ustreasury"
    country = "US"

    def _download(self, indicator, start, end, *, point_in_time, **_):
        frames = []
        for year in range(pd.Timestamp(start).year, pd.Timestamp(end).year + 1):
            params = {"type": "daily_treasury_yield_curve", "field_tdr_date_value": year}
            r = requests.get(BASE.format(year=year), params=params, timeout=30)
            r.raise_for_status()
            if r.text.strip():
                frames.append(pd.read_csv(io.StringIO(r.text)))
        if not frames:
            raise ValueError("treasury: no data")
        return pd.concat(frames, ignore_index=True)

    def to_observations(self, raw: pd.DataFrame, indicator, **_) -> list[MacroObservation]:
        col = TENORS.get(indicator.lower())
        if col is None:
            raise KeyError(f"unknown tenor '{indicator}'; known: {sorted(TENORS)}")
        if col not in raw.columns:
            raise KeyError(f"tenor column '{col}' not in Treasury response")
        df = raw[["Date", col]].copy()
        df["Date"] = pd.to_datetime(df["Date"])
        obs: list[MacroObservation] = []
        for _, row in df.iterrows():
            val = row[col]
            if pd.isna(val):
                continue
            d = row["Date"]
            obs.append(
                MacroObservation(
                    indicator_name=f"ust_{indicator.lower()}",
                    country="US",
                    period_start=d,
                    period_end=d,
                    release_date=d,  # yields published same business day
                    value=float(val),
                    unit="percent",
                    frequency="daily",
                    source="US Treasury",
                    source_url="https://home.treasury.gov/",
                    vintage_available=True,
                )
            )
        return obs
