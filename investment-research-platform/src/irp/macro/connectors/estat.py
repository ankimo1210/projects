"""e-Stat connector — Japanese government statistics (credential-gated).

Needs ``ESTAT_APP_ID`` (free) and a ``statsDataId`` (per-table; pass via the
``indicator`` or the ``SERIES`` map). e-Stat does not publish vintages, so
``release_date`` is estimated from the period and ``vintage_available=False`` (no
look-ahead guarantee for revisions — consistent with the platform's honesty rule).

The time-code parser is a documented heuristic for the common annual/monthly
forms; some tables encode time differently and need per-table adjustment. The JSON
extraction and parsing are tested offline against a fixture payload.
"""

from __future__ import annotations

import pandas as pd

from ...utils.config import env
from ..base import MacroConnector
from ..schema import MacroObservation

# Example statsDataId mappings (callers can pass any statsDataId directly).
SERIES: dict[str, str] = {
    # "jp_cpi": "0003427113",  # e.g. CPI table — fill in per the e-Stat catalog
}
_MISSING = {None, "", "-", "***", "X", "...", "－"}


def _parse_estat_time(code) -> pd.Timestamp | None:
    """Heuristic e-Stat ``@time`` parser: first 4 digits = year; digits 7-8 = month
    when present and valid, else year-end. Returns None if unparseable."""
    s = str(code)
    if len(s) < 4 or not s[:4].isdigit():
        return None
    year = int(s[:4])
    month = 12
    if len(s) >= 8 and s[6:8].isdigit() and 1 <= int(s[6:8]) <= 12:
        month = int(s[6:8])
    return pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)


class EStatConnector(MacroConnector):
    source = "estat"
    country = "JP"
    BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"

    def __init__(self, *a, app_id: str | None = None, **kw):
        super().__init__(*a, **kw)
        self.app_id = app_id or env("ESTAT_APP_ID")

    @staticmethod
    def extract_values(payload: dict) -> pd.DataFrame:
        """Pull the VALUE list out of an e-Stat getStatsData JSON payload."""
        try:
            vals = payload["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
        except (KeyError, TypeError):
            return pd.DataFrame(columns=["time", "value", "unit"])
        if isinstance(vals, dict):
            vals = [vals]
        rows = [
            {"time": v.get("@time"), "value": v.get("$"), "unit": v.get("@unit", "")} for v in vals
        ]
        return pd.DataFrame(rows)

    def _download(self, indicator, start, end, *, point_in_time, **_) -> pd.DataFrame:
        if not self.app_id:
            raise RuntimeError("ESTAT_APP_ID not set (free app id from e-stat.go.jp)")
        import requests

        params = {
            "appId": self.app_id,
            "statsDataId": SERIES.get(indicator, indicator),
            "limit": 100000,
        }
        r = requests.get(self.BASE, params=params, timeout=60)
        r.raise_for_status()
        return self.extract_values(r.json())

    def to_observations(self, raw: pd.DataFrame, indicator, **_) -> list[MacroObservation]:
        if raw.empty:
            return []
        obs: list[MacroObservation] = []
        for _, row in raw.iterrows():
            val = row.get("value")
            if val in _MISSING:
                continue
            try:
                fval = float(str(val).replace(",", ""))
            except (TypeError, ValueError):
                continue
            period = _parse_estat_time(row.get("time"))
            if period is None:
                continue
            obs.append(
                MacroObservation(
                    indicator_name=indicator,
                    country="JP",
                    period_start=period,
                    period_end=period,
                    release_date=period,  # no vintage -> estimated; flagged below
                    value=fval,
                    source="e-Stat",
                    source_url="https://www.e-stat.go.jp/",
                    unit=str(row.get("unit", "")),
                    vintage_available=False,
                )
            )
        return obs
