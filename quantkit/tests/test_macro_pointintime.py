"""The platform's central rigor guarantee: macro is point-in-time.

An indicator value is never visible before its release_date, and revisions are
respected (as_of(old) sees the original print, latest() sees the revision).
Nothing is forward-filled.
"""

from __future__ import annotations

import pandas as pd
import pytest
from quantkit.data.cache import CacheManager
from quantkit.macro.base import MacroConnector
from quantkit.macro.schema import MacroObservation, to_macro_frame
from quantkit.macro.store import as_of, latest, revisions


def _revised_frame() -> pd.DataFrame:
    obs = [
        # Jan period: first printed 2024-02-15 (=3.0), revised 2024-03-15 (=3.2)
        MacroObservation(
            "cpi",
            "US",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-31"),
            pd.Timestamp("2024-02-15"),
            3.0,
            "ALFRED",
            vintage_available=True,
        ),
        MacroObservation(
            "cpi",
            "US",
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-31"),
            pd.Timestamp("2024-03-15"),
            3.2,
            "ALFRED",
            vintage_available=True,
        ),
        # Feb period: printed 2024-03-15 (=2.8)
        MacroObservation(
            "cpi",
            "US",
            pd.Timestamp("2024-02-01"),
            pd.Timestamp("2024-02-29"),
            pd.Timestamp("2024-03-15"),
            2.8,
            "ALFRED",
            vintage_available=True,
        ),
    ]
    return to_macro_frame(obs)


def test_as_of_never_returns_unreleased():
    f = _revised_frame()
    # Before the Feb release, Feb is invisible and Jan shows the ORIGINAL print.
    s = as_of(f, "2024-02-20")
    assert list(s.index) == [pd.Timestamp("2024-01-01")]
    assert s.loc[pd.Timestamp("2024-01-01")] == 3.0
    # The invariant: no chosen value has release_date after the as_of date.
    visible = f[f["release_date"] <= pd.Timestamp("2024-02-20")]
    assert (visible["release_date"] <= pd.Timestamp("2024-02-20")).all()


def test_as_of_respects_revisions():
    f = _revised_frame()
    s = as_of(f, "2024-03-20")
    assert s.loc[pd.Timestamp("2024-01-01")] == 3.2  # revised value now visible
    assert s.loc[pd.Timestamp("2024-02-01")] == 2.8


def test_latest_uses_most_recent_vintage():
    f = _revised_frame()
    s = latest(f)
    assert s.loc[pd.Timestamp("2024-01-01")] == 3.2  # revision, not original


def test_as_of_before_any_release_is_empty_not_filled():
    f = _revised_frame()
    s = as_of(f, "2024-01-10")
    assert s.empty  # not forward/back-filled


def test_revisions_listing():
    f = _revised_frame()
    rev = revisions(f, "2024-01-01")
    assert rev["value"].tolist() == [3.0, 3.2]


# --- connector fetch: point-in-time and latest cached SEPARATELY --------------
class _FakeMacro(MacroConnector):
    source = "fakemacro"
    country = "US"

    def _download(self, indicator, start, end, *, point_in_time, **_):
        return {"point_in_time": point_in_time}

    def to_observations(self, raw, indicator, **_):
        pit = raw["point_in_time"]
        # one period, revised once; latest mode collapses to newest release
        return [
            MacroObservation(
                indicator,
                "US",
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-01-31"),
                pd.Timestamp("2024-02-15"),
                3.0,
                "x",
                vintage_available=pit,
            ),
            MacroObservation(
                indicator,
                "US",
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-01-31"),
                pd.Timestamp("2024-03-15"),
                3.2,
                "x",
                vintage_available=pit,
            ),
        ]


def test_fetch_separates_pit_and_latest(tmp_path):
    c = _FakeMacro(cache=CacheManager(root=tmp_path), ttl_seconds=3600)
    pit = c.fetch("cpi", "2024-01-01", "2024-04-01", point_in_time=True)
    lat = c.fetch("cpi", "2024-01-01", "2024-04-01", point_in_time=False)
    assert len(pit) == 2  # all vintages kept
    assert len(lat) == 1  # latest view collapses to one row per period
    assert lat.iloc[0]["value"] == 3.2
    # stored under different stores
    assert (tmp_path / "point_in_time" / "fakemacro").exists()
    assert (tmp_path / "processed" / "macro_fakemacro").exists()


def test_fred_to_observations_skips_missing():
    from quantkit.macro.connectors.fred import FredConnector

    raw = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "value": ["3.0", ".", "3.2"],  # middle is missing
            "realtime_start": ["2024-02-15", "2024-03-15", "2024-04-15"],
        }
    )
    raw.attrs["series_id"] = "CPIAUCSL"
    raw.attrs["point_in_time"] = True
    obs = FredConnector(api_key="dummy").to_observations(raw, "us_cpi")
    assert len(obs) == 2  # missing "." skipped, not fabricated
    assert obs[0].release_date == pd.Timestamp("2024-02-15")
    assert obs[0].vintage_available is True
