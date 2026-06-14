"""irp data layer: common Connector contract, caching, quality, and connectors.

High-level entry point is :func:`get_prices`, which honors the platform rule
"Stooq primary, yfinance fallback (with a warning)".
"""

from __future__ import annotations

import pandas as pd

from . import connectors, quality
from .base import OHLCV_COLUMNS, Connector, ConnectorError, FetchResult
from .cache import CacheManager
from .connectors import (
    BinanceConnector,
    CoinGeckoConnector,
    JQuantsConnector,
    StooqConnector,
    YFinanceConnector,
    get_connector,
)
from .fundamentals import SecEdgarConnector, fundamental_as_of
from .quality import DataQualityReport, assess

__all__ = [
    "OHLCV_COLUMNS",
    "BinanceConnector",
    "CacheManager",
    "CoinGeckoConnector",
    "Connector",
    "ConnectorError",
    "DataQualityReport",
    "FetchResult",
    "JQuantsConnector",
    "SecEdgarConnector",
    "StooqConnector",
    "YFinanceConnector",
    "assess",
    "connectors",
    "fundamental_as_of",
    "get_connector",
    "get_prices",
    "quality",
]


def get_prices(
    symbol: str,
    start,
    end=None,
    *,
    source: str = "auto",
    cache: CacheManager | None = None,
    **kwargs,
) -> FetchResult:
    """Fetch normalized OHLCV for one symbol.

    source="auto": try Stooq, fall back to yfinance (with a warning) on failure.
    Otherwise use the named source from the connector registry.
    """
    if source != "auto":
        return get_connector(source, cache=cache).fetch(symbol, start, end, **kwargs)

    try:
        return StooqConnector(cache=cache).fetch(symbol, start, end, **kwargs)
    except ConnectorError:
        return YFinanceConnector(cache=cache).fetch(symbol, start, end, **kwargs)


def price_panel(results: dict[str, FetchResult], field: str = "adj_close") -> pd.DataFrame:
    """Combine per-symbol FetchResults into a wide panel of one field.

    Aligns on the union of dates WITHOUT forward-filling (gaps stay NaN; the
    backtest layer decides how to treat non-trading days).
    """
    cols = {sym: fr.data[field] for sym, fr in results.items() if field in fr.data}
    return pd.DataFrame(cols).sort_index()
