"""Connector base class and the common data schema.

Every market-data connector implements the same contract:

    _download(symbol, start, end) -> raw DataFrame        # network, source-specific
    normalize(raw, symbol)        -> DataFrame            # common OHLCV schema

``fetch()`` wraps them with caching (raw + normalized), rate limiting, error
logging, and a data-quality report — so connectors only express *what* a source
returns, not the bookkeeping. Missing data is reported, never silently repaired.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd

from ..utils.dates import to_ts
from ..utils.logging import get_logger
from .cache import CacheManager
from .quality import DataQualityReport, assess

# Common normalized OHLCV schema (a connector may leave some columns NaN).
OHLCV_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


class ConnectorError(RuntimeError):
    """Raised when a download fails after retries (logged, not swallowed)."""


@dataclass
class FetchResult:
    symbol: str
    source: str
    data: pd.DataFrame
    quality: DataQualityReport
    meta: dict = field(default_factory=dict)
    from_cache: bool = False


class Connector(ABC):
    """Base for market-data (OHLCV / price) connectors."""

    #: short source id, used in cache paths and metadata (override in subclass)
    source: str = "base"
    #: columns the quality check requires to consider the schema valid
    required_columns: tuple[str, ...] = ("close",)

    def __init__(
        self,
        cache: CacheManager | None = None,
        *,
        rate_limit_s: float = 0.0,
        ttl_seconds: float | None = None,
        retries: int = 2,
    ):
        self.cache = cache or CacheManager()
        self.rate_limit_s = rate_limit_s
        self.ttl_seconds = ttl_seconds
        self.retries = retries
        self.log = get_logger(f"irp.data.{self.source}")
        self._last_call = 0.0

    # --- subclasses implement these two ------------------------------------
    @abstractmethod
    def _download(self, symbol: str, start, end, **kwargs) -> pd.DataFrame:
        """Return the source's RAW frame (as-is) for one symbol."""

    @abstractmethod
    def normalize(self, raw: pd.DataFrame, symbol: str, **kwargs) -> pd.DataFrame:
        """Map a raw frame to the common schema: a DatetimeIndex (ascending) and
        a subset of OHLCV_COLUMNS. No filling of gaps."""

    # --- the wrapper everyone calls ----------------------------------------
    def fetch(self, symbol: str, start, end=None, *, force: bool = False, **kwargs) -> FetchResult:
        start_ts = to_ts(start)
        end_ts = to_ts(end) if end is not None else pd.Timestamp.today().normalize()
        key = f"{symbol}_{start_ts.date()}_{end_ts.date()}"

        if not force and self.cache.is_fresh("processed", self.source, key, self.ttl_seconds):
            data = self.cache.read("processed", self.source, key)
            data.index = pd.to_datetime(data.index)
            q = assess(data, required_columns=list(self.required_columns), as_of=end_ts)
            return FetchResult(symbol, self.source, data, q, {"key": key}, from_cache=True)

        raw = self._download_cached(symbol, start_ts, end_ts, force=force, **kwargs)
        data = self.normalize(raw, symbol, **kwargs)
        data = data[data.index.notna()].sort_index()
        data = data.loc[(data.index >= start_ts) & (data.index <= end_ts)]
        self.cache.write("processed", self.source, key, data)
        q = assess(data, required_columns=list(self.required_columns), as_of=end_ts)
        for w in q.warnings:
            self.log.warning("%s: %s", symbol, w)
        return FetchResult(symbol, self.source, data, q, {"key": key}, from_cache=False)

    # --- internals ----------------------------------------------------------
    def _download_cached(self, symbol, start, end, *, force, **kwargs) -> pd.DataFrame:
        raw_key = f"{symbol}_{start.date()}_{end.date()}"
        if not force and self.cache.is_fresh("raw", self.source, raw_key, self.ttl_seconds):
            return self.cache.read("raw", self.source, raw_key)
        raw = self._download_with_retries(symbol, start, end, **kwargs)
        try:
            self.cache.write("raw", self.source, raw_key, raw)
        except Exception as e:  # raw caching is best-effort; don't fail the fetch
            self.log.warning("could not cache raw for %s: %s", symbol, e)
        return raw

    def _download_with_retries(self, symbol, start, end, **kwargs) -> pd.DataFrame:
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            self._respect_rate_limit()
            try:
                raw = self._download(symbol, start, end, **kwargs)
                if raw is None or len(raw) == 0:
                    raise ConnectorError(f"empty response for {symbol}")
                return raw
            except Exception as e:  # log and retry
                last = e
                self.log.warning("download %s attempt %d failed: %s", symbol, attempt + 1, e)
        raise ConnectorError(f"{self.source}: failed to download {symbol}: {last}") from last

    def _respect_rate_limit(self) -> None:
        if self.rate_limit_s <= 0:
            return
        wait = self.rate_limit_s - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
