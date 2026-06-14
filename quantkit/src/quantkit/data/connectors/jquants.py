"""J-Quants connector — Japanese equity daily OHLCV (free tier, credential-gated).

Needs a refresh token (``JQUANTS_REFRESH_TOKEN``); ``_download`` exchanges it for
an id token and pages through ``/prices/daily_quotes``. ``normalize`` maps the
J-Quants schema to the common OHLCV columns, using ``AdjustmentClose`` as
``adj_close``. The parser is tested offline against a sample payload (no network).

Symbols are J-Quants codes (e.g. ``"7203"`` Toyota; a trailing 0 / 5-digit form
is also accepted by the API).
"""

from __future__ import annotations

import pandas as pd
import requests

from ...utils.config import env
from ..base import Connector, ConnectorError

_AUTH_URL = "https://api.jquants.com/v1/token/auth_refresh"
_QUOTES_URL = "https://api.jquants.com/v1/prices/daily_quotes"


class JQuantsConnector(Connector):
    source = "jquants"

    def _id_token(self) -> str:
        refresh = env("JQUANTS_REFRESH_TOKEN")
        if not refresh:
            raise ConnectorError("jquants: JQUANTS_REFRESH_TOKEN not set (free account required)")
        r = requests.post(_AUTH_URL, params={"refreshtoken": refresh}, timeout=30)
        r.raise_for_status()
        token = r.json().get("idToken")
        if not token:
            raise ConnectorError("jquants: auth_refresh returned no idToken")
        return token

    def _download(self, symbol, start, end, **_) -> pd.DataFrame:
        token = self._id_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "code": str(symbol),
            "from": pd.Timestamp(start).strftime("%Y-%m-%d"),
            "to": pd.Timestamp(end).strftime("%Y-%m-%d"),
        }
        quotes: list[dict] = []
        pagination_key = None
        for _ in range(50):  # page through results
            p = dict(params)
            if pagination_key:
                p["pagination_key"] = pagination_key
            r = requests.get(_QUOTES_URL, headers=headers, params=p, timeout=30)
            r.raise_for_status()
            payload = r.json()
            quotes.extend(payload.get("daily_quotes", []))
            pagination_key = payload.get("pagination_key")
            if not pagination_key:
                break
        return pd.DataFrame(quotes)

    def normalize(self, raw: pd.DataFrame, symbol: str, **_) -> pd.DataFrame:
        if raw.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
        df = raw.copy()
        df["date"] = pd.to_datetime(df["Date"])
        df = df.set_index("date").sort_index()
        out = pd.DataFrame(index=df.index)
        for col, src in [
            ("open", "Open"),
            ("high", "High"),
            ("low", "Low"),
            ("close", "Close"),
            ("volume", "Volume"),
        ]:
            out[col] = pd.to_numeric(df[src], errors="coerce") if src in df else pd.NA
        adj = df["AdjustmentClose"] if "AdjustmentClose" in df else df.get("Close")
        out["adj_close"] = pd.to_numeric(adj, errors="coerce")
        return out
