"""Base class for macro-data connectors.

Like the market Connector, but the unit of data is a *macro frame* (one row per
observation/vintage, see schema.MACRO_COLUMNS). ``fetch`` caches point-in-time
frames separately from latest-vintage frames and reports data quality. Macro
series are never silently forward-filled.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

import pandas as pd

from ..data.cache import CacheManager
from ..utils.dates import to_ts
from ..utils.logging import get_logger
from .schema import MACRO_COLUMNS, MacroObservation, to_macro_frame


class MacroConnector(ABC):
    source: str = "macro-base"
    country: str = ""

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
        self.log = get_logger(f"quantkit.macro.{self.source}")
        self._last_call = 0.0

    @abstractmethod
    def _download(self, indicator: str, start, end, *, point_in_time: bool, **kwargs):
        """Return the source's raw payload for one indicator."""

    @abstractmethod
    def to_observations(self, raw, indicator: str, **kwargs) -> list[MacroObservation]:
        """Map a raw payload to MacroObservation rows (with release_date)."""

    def fetch(
        self, indicator: str, start, end=None, *, point_in_time: bool = False, force: bool = False
    ) -> pd.DataFrame:
        start_ts = to_ts(start)
        end_ts = to_ts(end) if end is not None else pd.Timestamp.today().normalize()
        kind = "point_in_time" if point_in_time else "processed"
        src = self.source if point_in_time else f"macro_{self.source}"
        key = f"{indicator}_{start_ts.date()}_{end_ts.date()}"

        if not force and self.cache.is_fresh(kind, src, key, self.ttl_seconds):
            frame = self.cache.read(kind, src, key)
            return self._coerce(frame)

        raw = self._download_with_retries(indicator, start_ts, end_ts, point_in_time=point_in_time)
        obs = self.to_observations(raw, indicator)
        frame = to_macro_frame(obs)
        if not point_in_time and not frame.empty:
            # latest view: keep the most recent release per period
            frame = (
                frame.sort_values("release_date")
                .groupby("period_start", as_index=False)
                .tail(1)
                .reset_index(drop=True)
            )
        self.cache.write(kind, src, key, frame)
        if frame.empty:
            self.log.warning("%s: no observations returned (NOT fabricated)", indicator)
        return self._coerce(frame)

    @staticmethod
    def _coerce(frame: pd.DataFrame) -> pd.DataFrame:
        for c in ("period_start", "period_end", "release_date", "vintage_date", "last_updated"):
            if c in frame:
                frame[c] = pd.to_datetime(frame[c], errors="coerce")
        return frame.reindex(columns=MACRO_COLUMNS)

    def _download_with_retries(self, indicator, start, end, *, point_in_time):
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            self._respect_rate_limit()
            try:
                return self._download(indicator, start, end, point_in_time=point_in_time)
            except Exception as e:
                last = e
                self.log.warning("download %s attempt %d failed: %s", indicator, attempt + 1, e)
        raise RuntimeError(f"{self.source}: failed to download {indicator}: {last}") from last

    def _respect_rate_limit(self) -> None:
        if self.rate_limit_s <= 0:
            return
        wait = self.rate_limit_s - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
