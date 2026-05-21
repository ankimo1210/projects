"""J-Quants API v2 provider (https://jpx-jquants.com/).

V2 uses API-key authentication via the `x-api-key` header. The API key is
issued in the dashboard and has no expiration (until revoked).

Required env (.env):
    JQUANTS_API_KEY=...      # preferred
    JQUANTS_REFRESH_TOKEN=...  # treated as API key (back-compat alias)

Free plan covers ~2 years of daily quotes (2024-02-16 .. 2026-02-16 today).
Endpoints used:
    GET /v2/equities/bars/daily    daily OHLCV (free plan)
    GET /v2/equities/master        listed-issue master (free plan)
    GET /v2/fins/details           financials (paid plan; falls back gracefully)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

from stockkit.data import cache as _cache
from stockkit.data.symbols import normalize_symbol

API_BASE = "https://api.jquants.com/v2"


class JQuantsError(RuntimeError):
    pass


def _api_key() -> str:
    load_dotenv()
    key = os.environ.get("JQUANTS_API_KEY") or os.environ.get("JQUANTS_REFRESH_TOKEN") or ""
    if not key:
        raise JQuantsError("JQUANTS_API_KEY (or JQUANTS_REFRESH_TOKEN) not set in .env")
    return key


def _headers() -> dict[str, str]:
    return {"x-api-key": _api_key()}


def is_configured() -> bool:
    load_dotenv()
    return bool(os.environ.get("JQUANTS_API_KEY") or os.environ.get("JQUANTS_REFRESH_TOKEN"))


def _to_jq_code(symbol: str) -> str:
    s = normalize_symbol(symbol)
    if s.endswith(".T"):
        s = s[:-2]
    return s


def _paged_get(path: str, params: dict) -> list[dict]:
    """Follow `pagination_key` until exhausted. Records live under `data`."""
    out: list[dict] = []
    p = dict(params)
    url = f"{API_BASE}{path}"
    while True:
        r = requests.get(url, params=p, headers=_headers(), timeout=30)
        if r.status_code >= 400:
            try:
                msg = r.json().get("message", r.text)
            except Exception:
                msg = r.text
            raise JQuantsError(f"{path} {r.status_code}: {msg}")
        data = r.json()
        rows = data.get("data") or []
        out.extend(rows)
        nxt = data.get("pagination_key")
        if not nxt:
            break
        p["pagination_key"] = nxt
    return out


# ---------- public API ----------

_BAR_COLMAP_ADJ = {
    "Date": "date",
    "AdjO": "open",
    "AdjH": "high",
    "AdjL": "low",
    "AdjC": "close",
    "AdjC2": "adj_close",  # never present, but kept symmetric
    "AdjVo": "volume",
}
_BAR_COLMAP_RAW = {
    "Date": "date",
    "O": "open",
    "H": "high",
    "L": "low",
    "C": "close",
    "Vo": "volume",
}


def jq_get_prices(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Daily quotes via /v2/equities/bars/daily.

    Returns OHLCV (adjusted) indexed by date. Cached in DuckDB under the
    .T-suffixed symbol so yfinance and J-Quants share the cache row space.
    """
    sym = normalize_symbol(symbol)
    code = _to_jq_code(sym)

    if not start:
        start = (datetime.utcnow() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    if not end:
        end = datetime.utcnow().strftime("%Y-%m-%d")

    if use_cache:
        last = _cache.latest_cached_date(sym)
        if last is not None and last >= pd.Timestamp(end) - pd.Timedelta(days=2):
            return _cache.read_prices(sym, start=start, end=end)

    rows = _paged_get(
        "/equities/bars/daily",
        {
            "code": code,
            "from": start.replace("-", ""),
            "to": end.replace("-", ""),
        },
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Prefer adjusted columns; fall back to raw if Adj* missing
    has_adj = "AdjC" in df.columns
    colmap = _BAR_COLMAP_ADJ if has_adj else _BAR_COLMAP_RAW
    df = df.rename(columns=colmap)
    df["date"] = pd.to_datetime(df["date"])

    # Build canonical columns. yfinance keeps both close and adj_close;
    # for J-Quants adjusted bars they're equal.
    out = pd.DataFrame(
        {
            "open": df.get("open"),
            "high": df.get("high"),
            "low": df.get("low"),
            "close": df.get("close"),
            "adj_close": df.get("close"),
            "volume": df.get("volume"),
        }
    )
    out.index = df["date"]
    out.index.name = "date"
    out = out.sort_index().dropna(subset=["close"])

    if use_cache:
        _cache.upsert_prices(sym, out)
        return _cache.read_prices(sym, start=start, end=end)
    return out


def jq_listed_master() -> pd.DataFrame:
    """Listed-issue master via /v2/equities/master."""
    rows = _paged_get("/equities/master", {})
    return pd.DataFrame(rows)


def jq_statements(symbol: str) -> pd.DataFrame:
    """Financials via /v2/fins/details (paid plan).

    Returns an empty DataFrame if the API responds with `not available on
    your subscription` rather than raising.
    """
    code = _to_jq_code(symbol)
    try:
        rows = _paged_get("/fins/details", {"code": code})
    except JQuantsError as e:
        if "subscription" in str(e):
            return pd.DataFrame()
        raise
    df = pd.DataFrame(rows)
    if not df.empty and "DisclosedDate" in df.columns:
        df["DisclosedDate"] = pd.to_datetime(df["DisclosedDate"])
        df = df.sort_values("DisclosedDate")
    return df
