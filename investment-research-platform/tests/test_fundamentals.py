"""SEC EDGAR fundamentals: concept parsing and point-in-time (filing-date) access.

Tested offline against a fixture companyfacts payload (no network), like the price
connectors. The key invariant: a fundamental value is only visible on/after its
filing date.
"""

from __future__ import annotations

import numpy as np
from irp.data.fundamentals import SecEdgarConnector, fundamental_as_of

_FACTS = {
    "cik": 320193,
    "entityName": "Example Inc.",
    "facts": {
        "us-gaap": {
            "NetIncomeLoss": {
                "label": "Net Income",
                "units": {
                    "USD": [
                        {
                            "end": "2021-12-31",
                            "val": 90.0,
                            "fy": 2021,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2022-02-15",
                        },
                        {
                            "end": "2022-12-31",
                            "val": 100.0,
                            "fy": 2022,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2023-02-15",
                        },
                        {
                            "end": "2020-12-31",
                            "val": None,
                            "fy": 2020,
                            "fp": "FY",
                            "form": "10-K",
                        },  # no 'filed' -> skipped
                    ]
                },
            }
        }
    },
}


def test_concept_observations_parses_and_sorts():
    obs = SecEdgarConnector.concept_observations(_FACTS, "NetIncomeLoss")
    assert list(obs.columns) == ["period_end", "filed", "value", "form", "fy", "fp"]
    assert len(obs) == 2  # the entry without 'filed' is dropped, not fabricated
    assert obs["value"].tolist() == [90.0, 100.0]  # sorted by filing date
    assert obs.iloc[0]["filed"].year == 2022


def test_concept_observations_missing_concept_is_empty():
    assert SecEdgarConnector.concept_observations(_FACTS, "Revenues").empty


def test_fundamental_as_of_is_point_in_time():
    obs = SecEdgarConnector.concept_observations(_FACTS, "NetIncomeLoss")
    # mid-2022: only FY2021 (filed 2022-02-15) is public yet
    assert fundamental_as_of(obs, "2022-06-01") == 90.0
    # mid-2023: FY2022 (filed 2023-02-15) now public
    assert fundamental_as_of(obs, "2023-06-01") == 100.0
    # before any filing: nothing visible (not back-filled)
    assert np.isnan(fundamental_as_of(obs, "2021-06-01"))
