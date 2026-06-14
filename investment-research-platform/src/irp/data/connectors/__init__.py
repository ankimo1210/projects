"""Market-data connectors (OHLCV / price). Stooq is primary; yfinance is fallback."""

from __future__ import annotations

from .binance import BinanceConnector
from .coingecko import CoinGeckoConnector
from .stooq import StooqConnector
from .yfinance_conn import YFinanceConnector

REGISTRY = {
    "stooq": StooqConnector,
    "yfinance": YFinanceConnector,
    "coingecko": CoinGeckoConnector,
    "binance": BinanceConnector,
}

__all__ = [
    "REGISTRY",
    "BinanceConnector",
    "CoinGeckoConnector",
    "StooqConnector",
    "YFinanceConnector",
]


def get_connector(source: str, **kwargs):
    """Instantiate a connector by source id (see REGISTRY)."""
    try:
        return REGISTRY[source](**kwargs)
    except KeyError:
        raise KeyError(f"unknown market source '{source}'; known: {sorted(REGISTRY)}") from None
