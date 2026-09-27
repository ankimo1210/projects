"""e-Stat (Japan Statistics Bureau) data provider.

Provides Japan CPI (Consumer Price Index) monthly data via the e-Stat API v3.

Required env (.env):
    ESTAT_API_KEY=<your key>
    Free registration at https://www.e-stat.go.jp/api/

Data:
    JP_CPI_ID = "0003427113"   # CPI 2020-base, national, all-items index
    series stored as "ESTAT:JP_CPI" in DuckDB macro_series table

Time code format in e-Stat API:
    Monthly:      "YYYY00MMHH"  e.g. "2026000303" → 2026-03-01
    Annual/other: contains "00" pattern that doesn't match monthly → skipped
"""

from __future__ import annotations

import os
import re
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

from stockkit.data import cache as _cache

JP_CPI_SERIES = "ESTAT:JP_CPI"
JP_CPI_STATS_ID = "0003427113"  # CPI 2020年基準

_API_BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
_MONTHLY_RE = re.compile(r"^(\d{4})00(\d{2})\d{2}$")
_STALE_DAYS = 28


class EStatError(RuntimeError):
    pass


def _api_key() -> str:
    load_dotenv()
    key = os.environ.get("ESTAT_API_KEY", "")
    if not key:
        raise EStatError(
            "ESTAT_API_KEY not set in .env. Register free at https://www.e-stat.go.jp/api/"
        )
    return key


def is_configured() -> bool:
    load_dotenv()
    return bool(os.environ.get("ESTAT_API_KEY"))


def estat_get_jp_cpi(
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
) -> pd.Series:
    """Fetch Japan CPI all-items index (2020=100) from e-Stat, monthly.

    Returns pd.Series indexed by date (1st of each month), named ESTAT:JP_CPI.
    """
    if use_cache:
        last = _cache.latest_macro_date(JP_CPI_SERIES)
        today = pd.Timestamp(datetime.utcnow().date())
        if last is not None and last >= today - pd.Timedelta(days=_STALE_DAYS):
            return _cache.read_macro(JP_CPI_SERIES, start=start, end=end)

    series = _fetch_all()
    if series.empty:
        return series

    if use_cache:
        _cache.upsert_macro(JP_CPI_SERIES, series)
        return _cache.read_macro(JP_CPI_SERIES, start=start, end=end)
    return _slice(series, start, end)


def _fetch_all() -> pd.Series:
    """Fetch full CPI time series (all months) with pagination."""
    records: list[dict] = []
    start_pos = 1
    limit = 500

    while True:
        r = requests.get(
            _API_BASE,
            params={
                "appId": _api_key(),
                "statsDataId": JP_CPI_STATS_ID,
                "cdTab": "1",  # 指数
                "cdCat01": "0001",  # 総合
                "cdArea": "00000",  # 全国
                "startPosition": start_pos,
                "limit": limit,
                "metaGetFlg": "N",
                "cntGetFlg": "N",
            },
            timeout=30,
        )
        if r.status_code >= 400:
            raise EStatError(f"e-Stat API error {r.status_code}: {r.text[:200]}")

        data = r.json()["GET_STATS_DATA"]["STATISTICAL_DATA"]
        values = data["DATA_INF"]["VALUE"]
        if isinstance(values, dict):
            values = [values]
        records.extend(values)

        total = int(data["RESULT_INF"]["TOTAL_NUMBER"])
        if start_pos + limit - 1 >= total:
            break
        start_pos += limit

    return _parse_records(records)


def _parse_records(records: list[dict]) -> pd.Series:
    rows: dict[pd.Timestamp, float] = {}
    for v in records:
        m = _MONTHLY_RE.match(v.get("@time", ""))
        if not m:
            continue  # skip fiscal-year entries (YYYY10XXXX pattern)
        year, month = int(m.group(1)), int(m.group(2))
        if month == 0 or month > 12:
            continue  # skip annual totals (YYYY000000 pattern)
        date = pd.Timestamp(year=year, month=month, day=1)
        try:
            rows[date] = float(v["$"])
        except (ValueError, KeyError):
            continue

    if not rows:
        return pd.Series(dtype=float, name=JP_CPI_SERIES)

    s = pd.Series(rows, name=JP_CPI_SERIES).sort_index()
    s.index.name = "date"
    return s


def _slice(s: pd.Series, start: str | None, end: str | None) -> pd.Series:
    if start:
        s = s.loc[s.index >= pd.Timestamp(start)]
    if end:
        s = s.loc[s.index <= pd.Timestamp(end)]
    return s
