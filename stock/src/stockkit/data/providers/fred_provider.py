"""FRED (Federal Reserve Economic Data) provider.

Fetches macro time series via the fredapi library.
Results are stored in the DuckDB `macro_series` table.

Required env (.env):
    FRED_API_KEY=<your key>   # free at https://fred.stlouisfed.org/docs/api/api_key.html

Predefined series IDs:
    JP_CPI = "JPNCPIALLMINMEI"   # Japan CPI All Items, monthly NSA (index 2015=100)
    US_CPI = "CPIAUCSL"           # US CPI All Urban Consumers, monthly SA
    US_10Y = "DGS10"              # US Treasury 10Y yield, daily (%)
    JP_10Y = "IRLTLT01JPM156N"   # Japan Long-term Govt Bond yield, monthly (%)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

from stockkit.data import cache as _cache

JP_CPI = "JPNCPIALLMINMEI"  # WARNING: FRED stopped updating this series at 2021-06. For recent data use e-Stat API.
US_CPI = "CPIAUCSL"
US_10Y = "DGS10"
JP_10Y = "IRLTLT01JPM156N"
JP_EXPORTS = "XTEXVA01JPM667S"   # Japan Exports, USD, SA monthly (latest: 2026-03)
JP_IMPORTS = "XTIMVA01JPM667S"   # Japan Imports, USD, SA monthly (latest: 2026-03)
JP_UNEMPLOYMENT = "LRUNTTTTJPM156S"  # Japan Unemployment Rate %, monthly (latest: 2026-03)
JP_IP = "JPNPROINDMISMEI"        # Japan Industrial Production index, monthly (stale: 2024-03)
JP_POLICY_RATE = "IRSTCB01JPM156N"   # Japan Policy Rate %, monthly (stale: 2023-12)
USDJPY = "DEXJPUS"               # USD/JPY exchange rate, daily (latest: 2026-05)

_DAILY_SERIES = {US_10Y, USDJPY}
_STALE_DAYS_DAILY = 1
_STALE_DAYS_MONTHLY = 28


class FredError(RuntimeError):
    pass


def _api_key() -> str:
    load_dotenv()
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        raise FredError("FRED_API_KEY not set in .env")
    return key


def is_configured() -> bool:
    load_dotenv()
    return bool(os.environ.get("FRED_API_KEY"))


def fred_get_series(
    series_id: str,
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
) -> pd.Series:
    """Fetch a FRED time series, cache in DuckDB macro_series table.

    Returns a pd.Series indexed by date, named series_id.
    """
    if not start:
        start = (datetime.utcnow() - timedelta(days=365 * 30)).strftime("%Y-%m-%d")
    if not end:
        end = datetime.utcnow().strftime("%Y-%m-%d")

    if use_cache:
        last = _cache.latest_macro_date(series_id)
        stale_days = (
            _STALE_DAYS_DAILY if series_id in _DAILY_SERIES else _STALE_DAYS_MONTHLY
        )
        if last is not None and last >= pd.Timestamp(end) - pd.Timedelta(days=stale_days):
            return _cache.read_macro(series_id, start=start, end=end)

    series = _fred_download(series_id, start, end)
    if series.empty:
        return series

    if use_cache:
        _cache.upsert_macro(series_id, series)
        return _cache.read_macro(series_id, start=start, end=end)
    return series


def _fred_download(series_id: str, start: str, end: str) -> pd.Series:
    try:
        from fredapi import Fred
    except ImportError as e:
        raise FredError("fredapi not installed; run: uv add fredapi") from e

    try:
        fred = Fred(api_key=_api_key())
        raw = fred.get_series(series_id, observation_start=start, observation_end=end)
    except Exception as e:
        raise FredError(f"FRED fetch failed for {series_id}: {e}") from e

    if raw is None or raw.empty:
        return pd.Series(dtype=float, name=series_id)

    s = raw.copy()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    s.index.name = "date"
    s.name = series_id
    return s.sort_index().dropna()
