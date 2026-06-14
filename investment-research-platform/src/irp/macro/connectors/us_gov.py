"""US government statistics: BLS, BEA, Census.

JSON APIs with documented response shapes (parsed below and tested offline against
fixtures). BLS works without a key for light use; BEA and Census require a free
key. None expose vintages -> ``vintage_available=False``. Period strings are parsed
tolerantly (annual / quarterly / monthly).
"""

from __future__ import annotations

import pandas as pd

from ...utils.config import env
from ..base import MacroConnector
from ..schema import MacroObservation


def _period_to_ts(year: int, period: str) -> pd.Timestamp | None:
    """Map a BLS/BEA-style period code to a period-end timestamp."""
    p = (period or "").upper().strip()
    if p.startswith("M") and p[1:].isdigit():
        m = int(p[1:])
        if 1 <= m <= 12:
            return pd.Timestamp(year=year, month=m, day=1) + pd.offsets.MonthEnd(0)
        return pd.Timestamp(year=year, month=12, day=31)  # M13 = annual avg
    if p.startswith("Q") and p[1:].isdigit():
        q = min(max(int(p[1:]), 1), 4)
        return pd.Timestamp(year=year, month=3 * q, day=1) + pd.offsets.MonthEnd(0)
    return pd.Timestamp(year=year, month=12, day=31)  # annual / unknown -> year end


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


class BlsConnector(MacroConnector):
    """Bureau of Labor Statistics (CPI, unemployment, ...). Key optional."""

    source = "bls"
    country = "US"
    BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    def __init__(self, *a, api_key: str | None = None, **kw):
        super().__init__(*a, **kw)
        self.api_key = api_key or env("BLS_API_KEY")

    def _download(self, indicator, start, end, *, point_in_time, **_) -> pd.DataFrame:
        import requests

        body = {
            "seriesid": [indicator],
            "startyear": str(pd.Timestamp(start).year),
            "endyear": str(pd.Timestamp(end).year),
        }
        if self.api_key:
            body["registrationkey"] = self.api_key
        r = requests.post(self.BASE, json=body, timeout=60)
        r.raise_for_status()
        series = r.json().get("Results", {}).get("series", [])
        rows = series[0].get("data", []) if series else []
        return pd.DataFrame(rows)

    def to_observations(self, raw: pd.DataFrame, indicator, **_) -> list[MacroObservation]:
        if raw.empty:
            return []
        obs = []
        for _, row in raw.iterrows():
            val = _num(row.get("value"))
            if val is None:
                continue
            period = _period_to_ts(int(row["year"]), row.get("period", ""))
            if period is None:
                continue
            obs.append(_obs(indicator, "US", period, val, "BLS", "https://www.bls.gov/"))
        return obs


class BeaConnector(MacroConnector):
    """Bureau of Economic Analysis (GDP, PCE, ...). Requires BEA_API_KEY."""

    source = "bea"
    country = "US"
    BASE = "https://apps.bea.gov/api/data/"

    def __init__(self, *a, api_key: str | None = None, **kw):
        super().__init__(*a, **kw)
        self.api_key = api_key or env("BEA_API_KEY")

    def _download(self, indicator, start, end, *, point_in_time, **params) -> pd.DataFrame:
        import requests

        if not self.api_key:
            raise RuntimeError("BEA_API_KEY not set (free key from apps.bea.gov/API/signup)")
        q = {"UserID": self.api_key, "method": "GetData", "ResultFormat": "JSON", **params}
        r = requests.get(self.BASE, params=q, timeout=60)
        r.raise_for_status()
        data = r.json().get("BEAAPI", {}).get("Results", {}).get("Data", [])
        return pd.DataFrame(data)

    def to_observations(self, raw: pd.DataFrame, indicator, **_) -> list[MacroObservation]:
        if raw.empty:
            return []
        obs = []
        for _, row in raw.iterrows():
            val = _num(row.get("DataValue"))
            tp = str(row.get("TimePeriod", ""))
            if val is None or len(tp) < 4 or not tp[:4].isdigit():
                continue
            year = int(tp[:4])
            period_code = tp[4:] or ""  # "", "Q1", "M03"
            period = _period_to_ts(year, period_code.replace("Q", "Q").replace("M", "M"))
            obs.append(_obs(indicator, "US", period, val, "BEA", "https://www.bea.gov/"))
        return obs


class CensusConnector(MacroConnector):
    """US Census economic time series. Requires CENSUS_API_KEY. Array-of-arrays JSON."""

    source = "census"
    country = "US"
    BASE = "https://api.census.gov/data/timeseries"

    def __init__(self, *a, api_key: str | None = None, **kw):
        super().__init__(*a, **kw)
        self.api_key = api_key or env("CENSUS_API_KEY")

    @staticmethod
    def parse_rows(payload: list) -> pd.DataFrame:
        """Census returns [[header...], [row...], ...]; first row is the header."""
        if not payload or len(payload) < 2:
            return pd.DataFrame()
        return pd.DataFrame(payload[1:], columns=payload[0])

    def _download(self, indicator, start, end, *, point_in_time, dataset="eits/resconst", **params):
        import requests

        if not self.api_key:
            raise RuntimeError(
                "CENSUS_API_KEY not set (free key from api.census.gov/data/key_signup.html)"
            )
        q = {"get": indicator, "key": self.api_key, **params}
        r = requests.get(f"{self.BASE}/{dataset}", params=q, timeout=60)
        r.raise_for_status()
        return self.parse_rows(r.json())

    def to_observations(self, raw: pd.DataFrame, indicator, **_) -> list[MacroObservation]:
        if raw.empty or "time" not in raw.columns or indicator not in raw.columns:
            return []
        obs = []
        for _, row in raw.iterrows():
            val = _num(row.get(indicator))
            period = pd.to_datetime(row.get("time"), errors="coerce")
            if val is None or pd.isna(period):
                continue
            obs.append(_obs(indicator, "US", period, val, "Census", "https://www.census.gov/"))
        return obs


def _obs(indicator, country, period, value, source, url) -> MacroObservation:
    return MacroObservation(
        indicator_name=indicator,
        country=country,
        period_start=period,
        period_end=period,
        release_date=period,
        value=float(value),
        source=source,
        source_url=url,
        vintage_available=False,
    )
