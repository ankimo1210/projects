"""J-Quants (JP equities) and e-Stat (JP macro) connectors — offline tests.

No network and no credentials: ``normalize`` is fed a sample payload directly,
and ``_download`` runs against a fake ``requests.get`` that records the request.
The fake matters — parsing-only tests stayed green while the connector pointed at
the retired V1 API, so the request contract (host, path, auth header, date format,
payload key) is asserted here too.
"""

from __future__ import annotations

import pandas as pd
import pytest
from quantkit.data.base import ConnectorError
from quantkit.data.connectors import JQuantsConnector
from quantkit.macro.connectors.estat import EStatConnector


def test_jquants_normalize_maps_v2_adjusted_bars_to_ohlcv():
    """V2 /equities/bars/daily returns Adj* column names, not V1's Open/High/Low."""
    raw = pd.DataFrame(
        [
            {
                "Date": "2023-01-04",
                "Code": "7203",
                "AdjO": 1800,
                "AdjH": 1820,
                "AdjL": 1790,
                "AdjC": 1810,
                "AdjVo": 1_000_000,
            },
            {
                "Date": "2023-01-05",
                "Code": "7203",
                "AdjO": 1810,
                "AdjH": 1850,
                "AdjL": 1805,
                "AdjC": 1840,
                "AdjVo": 1_200_000,
            },
        ]
    )
    out = JQuantsConnector().normalize(raw, "7203")
    assert list(out.columns) == ["open", "high", "low", "close", "volume", "adj_close"]
    assert out.index.is_monotonic_increasing
    assert out.loc["2023-01-05", "close"] == 1840
    assert out.loc["2023-01-04", "adj_close"] == 1810


def test_jquants_normalize_falls_back_to_unadjusted_columns():
    raw = pd.DataFrame([{"Date": "2023-01-04", "O": 100, "H": 110, "L": 99, "C": 105, "Vo": 500}])
    out = JQuantsConnector().normalize(raw, "7203")
    assert out.loc["2023-01-04", "close"] == 105
    assert out.loc["2023-01-04", "high"] == 110
    assert out.loc["2023-01-04", "volume"] == 500


def test_jquants_empty_payload_is_empty_frame():
    out = JQuantsConnector().normalize(pd.DataFrame(), "7203")
    assert out.empty


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._payload


def _fake_get(calls, pages):
    def get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return _FakeResponse(pages[len(calls) - 1])

    return get


def test_jquants_download_calls_v2_bars_endpoint_with_api_key_header(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_KEY", "key-123")
    calls: list[dict] = []
    monkeypatch.setattr(
        "quantkit.data.connectors.jquants.requests.get",
        _fake_get(calls, [{"data": [{"Date": "2023-01-04", "AdjC": 1810}]}]),
    )

    raw = JQuantsConnector()._download("7203", "2023-01-04", "2023-01-05")

    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.jquants.com/v2/equities/bars/daily"
    assert calls[0]["headers"] == {"x-api-key": "key-123"}
    # V2 wants compact dates, and there is no Bearer id-token exchange any more.
    assert calls[0]["params"]["from"] == "20230104"
    assert calls[0]["params"]["to"] == "20230105"
    assert calls[0]["params"]["code"] == "7203"
    assert len(raw) == 1


def test_jquants_download_reads_data_key_and_follows_pagination(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_KEY", "key-123")
    calls: list[dict] = []
    pages = [
        {"data": [{"Date": "2023-01-04", "AdjC": 1810}], "pagination_key": "p2"},
        {"data": [{"Date": "2023-01-05", "AdjC": 1840}]},
    ]
    monkeypatch.setattr("quantkit.data.connectors.jquants.requests.get", _fake_get(calls, pages))

    raw = JQuantsConnector()._download("7203", "2023-01-04", "2023-01-05")

    assert len(raw) == 2  # V2 nests rows under "data", not "daily_quotes"
    assert calls[1]["params"]["pagination_key"] == "p2"


def test_jquants_download_accepts_refresh_token_env_as_api_key(monkeypatch):
    """The V2 key and the old refresh-token string are the same value in practice."""
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "legacy-value")
    calls: list[dict] = []
    monkeypatch.setattr(
        "quantkit.data.connectors.jquants.requests.get", _fake_get(calls, [{"data": []}])
    )

    JQuantsConnector()._download("7203", "2023-01-04", "2023-01-05")

    assert calls[0]["headers"] == {"x-api-key": "legacy-value"}


def test_jquants_download_without_credentials_raises(monkeypatch):
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(ConnectorError, match="JQUANTS_API_KEY"):
        JQuantsConnector()._download("7203", "2023-01-04", "2023-01-05")


def test_jquants_download_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_KEY", "key-123")

    class _ErrorResponse:
        status_code = 410
        text = "Gone"

        def json(self):
            return {"message": "This version has been retired"}

    monkeypatch.setattr(
        "quantkit.data.connectors.jquants.requests.get",
        lambda url, **kw: _ErrorResponse(),
    )
    with pytest.raises(ConnectorError, match="410"):
        JQuantsConnector()._download("7203", "2023-01-04", "2023-01-05")


_ESTAT_PAYLOAD = {
    "GET_STATS_DATA": {
        "STATISTICAL_DATA": {
            "DATA_INF": {
                "VALUE": [
                    {"@time": "2020000303", "@unit": "index", "$": "101.5"},
                    {"@time": "2021000303", "@unit": "index", "$": "103.2"},
                    {"@time": "2022000303", "@unit": "index", "$": "-"},  # missing
                ]
            }
        }
    }
}


def test_estat_extract_values():
    df = EStatConnector.extract_values(_ESTAT_PAYLOAD)
    assert len(df) == 3 and list(df.columns) == ["time", "value", "unit"]
    assert EStatConnector.extract_values({}).empty  # malformed -> empty, no crash


def test_estat_to_observations_parses_and_skips_missing():
    df = EStatConnector.extract_values(_ESTAT_PAYLOAD)
    obs = EStatConnector(app_id="x").to_observations(df, "jp_cpi")
    assert len(obs) == 2  # the "-" missing value is skipped, not fabricated
    assert obs[0].value == 101.5
    assert obs[0].country == "JP"
    assert obs[0].period_start == pd.Timestamp("2020-03-31")  # heuristic month parse
    assert obs[0].vintage_available is False  # e-Stat has no vintages
