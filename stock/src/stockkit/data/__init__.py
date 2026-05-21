"""Data access layer.

Default behaviour:
  - US tickers -> yfinance
  - JP tickers (4-digit or .T) -> yfinance unless J-Quants is configured;
    set source='jquants' to force.
  - Stooq-only tickers (e.g. ^tpx) -> stooq automatically

`get_prices(symbol, source='auto'|'yfinance'|'jquants'|'stooq', ...)`.
`get_macro(series_id, ...)` -> pd.Series  (CPI, bond yields via FRED)
`get_jp_cpi(...)` -> pd.Series  (Japan CPI monthly via e-Stat API)
"""

from __future__ import annotations

import pandas as pd

from stockkit.data.symbols import is_japanese, normalize_symbol
from stockkit.data.providers import yfinance_provider as _yf
from stockkit.data.providers import jquants_provider as _jq
from stockkit.data.providers import stooq_provider as _stooq
from stockkit.data.providers import fred_provider as _fred
from stockkit.data.providers import estat_provider as _estat

__all__ = [
    "get_prices",
    "get_info",
    "get_financials",
    "get_macro",
    "get_jp_cpi",
    "normalize_symbol",
    "is_japanese",
    "list_jp_securities",
]

# Tickers that only exist on Stooq (not in yfinance)
_STOOQ_ONLY = {"^TPX"}



def get_prices(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    period: str = "5y",
    use_cache: bool = True,
    source: str = "auto",
) -> pd.DataFrame:
    src = _resolve_source(symbol, source)
    if src == "jquants":
        return _jq.jq_get_prices(symbol, start=start, end=end, use_cache=use_cache)
    if src == "stooq":
        return _stooq.stooq_get_prices(symbol, start=start, end=end, use_cache=use_cache)
    return _yf.get_prices(
        symbol, start=start, end=end, period=period, use_cache=use_cache
    )


def get_info(symbol: str, source: str = "auto") -> dict:
    return _yf.get_info(symbol)


def get_financials(symbol: str, source: str = "auto"):
    src = _resolve_source(symbol, source)
    if src == "jquants":
        return {"jquants": _jq.jq_statements(symbol)}
    return _yf.get_financials(symbol)


def get_macro(
    series_id: str,
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
) -> pd.Series:
    """Fetch a macro time series from FRED (CPI, bond yields, etc.).

    series_id examples:
        fred_provider.JP_CPI  = "JPNCPIALLMINMEI"  # Japan CPI, monthly
        fred_provider.US_CPI  = "CPIAUCSL"          # US CPI, monthly
        fred_provider.US_10Y  = "DGS10"             # US 10Y yield, daily
        fred_provider.JP_10Y  = "IRLTLT01JPM156N"   # Japan 10Y yield, monthly
    """
    return _fred.fred_get_series(series_id, start=start, end=end, use_cache=use_cache)


def get_jp_cpi(
    start: str | None = None,
    end: str | None = None,
    use_cache: bool = True,
) -> pd.Series:
    """Fetch Japan CPI all-items index (2020=100) from e-Stat, monthly.

    Requires ESTAT_API_KEY in .env.
    Returns pd.Series indexed by date (1st of each month).
    Covers 2020年1月 〜 latest (approx. 2-month lag).
    """
    return _estat.estat_get_jp_cpi(start=start, end=end, use_cache=use_cache)


def list_jp_securities() -> pd.DataFrame:
    """JPX listed-issue master (requires J-Quants)."""
    return _jq.jq_listed_master()


def _resolve_source(symbol: str, source: str) -> str:
    if source == "yfinance":
        return "yfinance"
    if source == "jquants":
        return "jquants"
    if source == "stooq":
        return "stooq"
    # auto: Stooq-only tickers take priority (requires STOOQ_API_KEY)
    if symbol.upper() in _STOOQ_ONLY and _stooq.is_configured():
        return "stooq"
    # auto: prefer jquants for JP stocks if configured
    if is_japanese(symbol) and _jq.is_configured():
        return "jquants"
    return "yfinance"
