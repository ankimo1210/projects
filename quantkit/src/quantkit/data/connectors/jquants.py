"""J-Quants connector — Japanese equity daily OHLCV (free tier, credential-gated).

Uses **API v2**. V1 was retired and every V1 endpoint now answers ``HTTP 410 Gone``,
so there is no id-token exchange any more: v2 authenticates with a static
``x-api-key`` header. The key is issued in the J-Quants dashboard; in practice the
string previously stored as ``JQUANTS_REFRESH_TOKEN`` is that same value, so both
``JQUANTS_API_KEY`` and ``JQUANTS_REFRESH_TOKEN`` are accepted.

``_download`` pages through ``/v2/equities/bars/daily`` (rows under ``data``,
cursor in ``pagination_key``) and ``normalize`` maps the v2 bar schema to the
common OHLCV columns, preferring the adjusted series (``AdjO``/``AdjH``/``AdjL``/
``AdjC``/``AdjVo``) and falling back to the unadjusted one (``O``/``H``/``L``/
``C``/``Vo``). Both the parsing and the request contract are covered offline in
``tests/test_connectors_jp.py`` — parsing-only tests are what let this connector
sit broken on V1 while the suite stayed green.

Symbols are J-Quants codes (e.g. ``"7203"`` Toyota; a trailing 0 / 5-digit form
is also accepted by the API).
"""

from __future__ import annotations

import pandas as pd
import requests

from ...utils.config import env
from ..base import Connector, ConnectorError

_API_BASE = "https://api.jquants.com/v2"
_BARS_PATH = "/equities/bars/daily"
_MAX_PAGES = 50

#: v2 bar columns, adjusted for splits (preferred) and raw (fallback).
_ADJUSTED_COLUMNS = {
    "open": "AdjO",
    "high": "AdjH",
    "low": "AdjL",
    "close": "AdjC",
    "volume": "AdjVo",
}
_RAW_COLUMNS = {"open": "O", "high": "H", "low": "L", "close": "C", "volume": "Vo"}


class JQuantsConnector(Connector):
    source = "jquants"

    def _api_key(self) -> str:
        key = env("JQUANTS_API_KEY") or env("JQUANTS_REFRESH_TOKEN")
        if not key:
            raise ConnectorError(
                "jquants: JQUANTS_API_KEY not set (free account required; "
                "JQUANTS_REFRESH_TOKEN is accepted as an alias)"
            )
        return key

    def _download(self, symbol, start, end, **_) -> pd.DataFrame:
        headers = {"x-api-key": self._api_key()}
        params = {
            "code": str(symbol),
            "from": pd.Timestamp(start).strftime("%Y%m%d"),
            "to": pd.Timestamp(end).strftime("%Y%m%d"),
        }
        rows: list[dict] = []
        pagination_key = None
        for _page in range(_MAX_PAGES):
            p = dict(params)
            if pagination_key:
                p["pagination_key"] = pagination_key
            r = requests.get(f"{_API_BASE}{_BARS_PATH}", headers=headers, params=p, timeout=30)
            if r.status_code >= 400:
                raise ConnectorError(f"jquants: {_BARS_PATH} {r.status_code}: {_error_message(r)}")
            payload = r.json()
            rows.extend(payload.get("data") or [])
            pagination_key = payload.get("pagination_key")
            if not pagination_key:
                break
        return pd.DataFrame(rows)

    def normalize(self, raw: pd.DataFrame, symbol: str, **_) -> pd.DataFrame:
        if raw.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "adj_close", "volume"])
        df = raw.copy()
        df["date"] = pd.to_datetime(df["Date"])
        df = df.set_index("date").sort_index()
        adjusted = "AdjC" in df.columns
        columns = _ADJUSTED_COLUMNS if adjusted else _RAW_COLUMNS
        out = pd.DataFrame(index=df.index)
        for col, src in columns.items():
            out[col] = pd.to_numeric(df[src], errors="coerce") if src in df else pd.NA
        # v2 adjusted bars are already split-adjusted, so close is the adjusted close.
        out["adj_close"] = out["close"]
        return out


def _error_message(response) -> str:
    try:
        return response.json().get("message", response.text)
    except Exception:  # non-JSON error body
        return response.text
