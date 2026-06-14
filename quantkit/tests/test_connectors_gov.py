"""Offline parser tests for the government-statistics connectors:
BoJ / MoF (JP CSV) and BLS / BEA / Census (US JSON), plus EDINET document discovery.
Parsers are tested against fixtures matching the documented response shapes
(no network/keys); period parsing and missing-value handling are checked.
"""

from __future__ import annotations

import pandas as pd
from quantkit.data.fundamentals import EdinetConnector
from quantkit.macro.connectors.jp_extra import BoJConnector, MofConnector
from quantkit.macro.connectors.us_gov import BeaConnector, BlsConnector, CensusConnector


# --- BoJ / MoF (JP CSV) -------------------------------------------------------
def test_boj_parses_date_value_rows_only():
    csv = '"Series","ABC"\n"Date","value"\n"2020/1",-0.1\n"2020/2",-0.1\n"junk","x"\n'
    df = BoJConnector.parse_csv(csv)
    assert len(df) == 2  # header + junk lines skipped
    obs = BoJConnector().to_observations(df, "boj_policy_rate")
    assert len(obs) == 2 and obs[0].value == -0.1 and obs[0].vintage_available is False


def test_mof_picks_tenor_column():
    csv = "Date,2Y,10Y,30Y\n2024-01-04,0.05,0.62,1.65\n2024-01-05,0.06,0.60,1.63\n"
    df = MofConnector.parse_csv(csv, tenor="10Y")
    assert df["value"].tolist() == [0.62, 0.60]
    obs = MofConnector().to_observations(df, "10Y")
    assert obs[0].country == "JP" and obs[1].value == 0.60


# --- BLS / BEA / Census (US JSON) ---------------------------------------------
def test_bls_parses_monthly_periods():
    raw = pd.DataFrame(
        [
            {"year": "2024", "period": "M03", "value": "3.5"},
            {"year": "2024", "period": "M02", "value": "3.2"},
            {"year": "2024", "period": "M01", "value": "-"},  # non-numeric -> skipped
        ]
    )
    obs = BlsConnector().to_observations(raw, "CUUR0000SA0")
    assert len(obs) == 2
    march = next(o for o in obs if o.value == 3.5)
    assert march.period_start == pd.Timestamp("2024-03-31")


def test_bea_parses_timeperiod_and_commas():
    raw = pd.DataFrame(
        [
            {"TimePeriod": "2023Q4", "DataValue": "27,610.1"},
            {"TimePeriod": "2024", "DataValue": "28,000.0"},
        ]
    )
    obs = BeaConnector().to_observations(raw, "GDP")
    assert obs[0].value == 27610.1
    assert obs[0].period_start == pd.Timestamp("2023-12-31")  # Q4 -> Dec end
    assert obs[1].period_start == pd.Timestamp("2024-12-31")  # annual -> year end


def test_census_parse_rows_and_observations():
    payload = [
        ["cell_value", "time", "category_code"],
        ["1500", "2024-01", "TOTAL"],
        ["1600", "2024-02", "TOTAL"],
    ]
    df = CensusConnector.parse_rows(payload)
    assert list(df.columns) == ["cell_value", "time", "category_code"]
    obs = CensusConnector().to_observations(df, "cell_value")
    assert len(obs) == 2 and obs[0].value == 1500.0


# --- EDINET (JP disclosures) --------------------------------------------------
def test_edinet_parse_documents():
    payload = {
        "metadata": {"status": "200"},
        "results": [
            {
                "docID": "S100ABCD",
                "filerName": "Example KK",
                "secCode": "72030",
                "docTypeCode": "120",
                "periodEnd": "2024-03-31",
            },
            {
                "docID": "S100EFGH",
                "filerName": "Another KK",
                "secCode": "99840",
                "docTypeCode": "120",
                "periodEnd": "2024-03-31",
            },
        ],
    }
    df = EdinetConnector.parse_documents(payload)
    assert len(df) == 2 and "docID" in df.columns
    assert df.iloc[0]["filerName"] == "Example KK"
    assert EdinetConnector.parse_documents({"results": []}).empty
