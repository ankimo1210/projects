"""yfinance connector — FALLBACK only (Stooq is primary). Emits a warning on use,
per the platform rule that yfinance is a fallback with a data-quality caveat.

Handles Japanese tickers (e.g. ``7203.T``) and most US symbols. (Prior art:
stockkit's yfinance_provider.)
"""

from __future__ import annotations

import pandas as pd

from ..base import Connector


class YFinanceConnector(Connector):
    source = "yfinance"

    def _download(self, symbol, start, end, **_) -> pd.DataFrame:
        import yfinance as yf

        self.log.warning("using yfinance FALLBACK for %s (prefer Stooq; data may differ)", symbol)
        raw = yf.download(
            symbol,
            start=pd.Timestamp(start),
            end=pd.Timestamp(end) + pd.Timedelta(days=1),
            auto_adjust=False,
            progress=False,
        )
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        return raw

    def normalize(self, raw: pd.DataFrame, symbol: str, **_) -> pd.DataFrame:
        df = raw.rename(columns={c: str(c).lower().replace(" ", "_") for c in raw.columns})
        out = pd.DataFrame(index=pd.to_datetime(df.index))
        out.index.name = "date"
        for col in ("open", "high", "low", "close", "volume"):
            out[col] = pd.to_numeric(df[col], errors="coerce") if col in df else pd.NA
        out["adj_close"] = (
            pd.to_numeric(df["adj_close"], errors="coerce") if "adj_close" in df else out["close"]
        )
        return out.sort_index()
