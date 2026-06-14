"""FRED / ALFRED connector (US + some global macro & rates).

- point_in_time=False: latest observations (revised values).
- point_in_time=True: ALFRED vintages — each row's ``realtime_start`` is the date
  that value became available, used directly as ``release_date`` so ``as_of`` is
  exact.

Requires ``FRED_API_KEY`` (free). Get one at https://fred.stlouisfed.org/.
"""

from __future__ import annotations

import pandas as pd
import requests

from ..base import MacroConnector
from ..schema import MacroObservation

# A few common series ids (callers can pass any FRED series id directly).
SERIES = {
    "us_cpi": "CPIAUCSL",
    "us_core_cpi": "CPILFESL",
    "us_unemployment": "UNRATE",
    "us_fed_funds": "FEDFUNDS",
    "us_10y": "DGS10",
    "us_2y": "DGS2",
    "us_3m": "DGS3MO",
    "us_10y_2y": "T10Y2Y",
    "jp_cpi": "JPNCPIALLMINMEI",
    "jp_policy_rate": "IRSTCI01JPM156N",
    "usdjpy": "DEXJPUS",
}


class FredConnector(MacroConnector):
    source = "fred"
    country = "US"
    BASE = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, *a, api_key: str | None = None, **kw):
        from ...utils.config import env

        super().__init__(*a, **kw)
        self.api_key = api_key or env("FRED_API_KEY")

    def _download(self, indicator, start, end, *, point_in_time, **_):
        if not self.api_key:
            raise RuntimeError("FRED_API_KEY is not set (free key from fred.stlouisfed.org)")
        series_id = SERIES.get(indicator, indicator)
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": pd.Timestamp(start).strftime("%Y-%m-%d"),
            "observation_end": pd.Timestamp(end).strftime("%Y-%m-%d"),
        }
        if point_in_time:
            # ALFRED: ask for all vintages in the realtime window
            params["realtime_start"] = "1900-01-01"
            params["realtime_end"] = pd.Timestamp(end).strftime("%Y-%m-%d")
        r = requests.get(self.BASE, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        df = pd.DataFrame(payload.get("observations", []))
        df.attrs["series_id"] = series_id
        df.attrs["point_in_time"] = point_in_time
        return df

    def to_observations(self, raw: pd.DataFrame, indicator, **_) -> list[MacroObservation]:
        if raw.empty:
            return []
        series_id = raw.attrs.get("series_id", indicator)
        pit = raw.attrs.get("point_in_time", False)
        url = f"https://fred.stlouisfed.org/series/{series_id}"
        country = "JP" if indicator.startswith("jp") else self.country
        obs: list[MacroObservation] = []
        for _, row in raw.iterrows():
            val = row.get("value", ".")
            if val in (".", "", None):
                continue  # missing — skipped, never fabricated
            period = pd.to_datetime(row["date"])
            release = pd.to_datetime(row.get("realtime_start")) if pit else None
            obs.append(
                MacroObservation(
                    indicator_name=indicator,
                    country=country,
                    period_start=period,
                    period_end=period,
                    release_date=release if release is not None else period,
                    value=float(val),
                    source="FRED" if not pit else "ALFRED",
                    source_url=url,
                    vintage_date=pd.to_datetime(row.get("realtime_start")) if pit else None,
                    vintage_available=bool(pit),
                )
            )
        return obs
