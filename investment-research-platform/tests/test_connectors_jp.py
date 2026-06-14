"""J-Quants (JP equities) and e-Stat (JP macro) connectors — offline parsing tests.

Network/credentials are never required: a sample payload is fed to ``normalize`` /
``to_observations`` directly, mirroring the stooq/FRED connector tests.
"""

from __future__ import annotations

import pandas as pd
from irp.data.connectors import JQuantsConnector
from irp.macro.connectors.estat import EStatConnector


def test_jquants_normalize_maps_to_ohlcv():
    raw = pd.DataFrame(
        [
            {
                "Date": "2023-01-04",
                "Code": "7203",
                "Open": 1800,
                "High": 1820,
                "Low": 1790,
                "Close": 1810,
                "Volume": 1_000_000,
                "AdjustmentClose": 1810,
            },
            {
                "Date": "2023-01-05",
                "Code": "7203",
                "Open": 1810,
                "High": 1850,
                "Low": 1805,
                "Close": 1840,
                "Volume": 1_200_000,
                "AdjustmentClose": 1840,
            },
        ]
    )
    out = JQuantsConnector().normalize(raw, "7203")
    assert list(out.columns) == ["open", "high", "low", "close", "volume", "adj_close"]
    assert out.index.is_monotonic_increasing
    assert out.loc["2023-01-05", "close"] == 1840
    assert out.loc["2023-01-04", "adj_close"] == 1810


def test_jquants_empty_payload_is_empty_frame():
    out = JQuantsConnector().normalize(pd.DataFrame(), "7203")
    assert out.empty


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
