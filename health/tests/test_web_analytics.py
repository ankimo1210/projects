"""Regression tests for the frontend's pure analytical contract."""

import json

import pandas as pd
import pytest
from health.analytics import rolling_baseline_z
from health.web_analytics import build_analytics, clip_calendar


def test_baseline_uses_history_before_visible_window():
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=80),
            "resting_hr": [60 + i % 7 for i in range(80)],
        }
    )
    result = build_analytics(frame, pd.DataFrame())
    expected = rolling_baseline_z(frame, "resting_hr")
    rows = result["baselines"]["resting_hr"]
    assert rows[-1]["z"] == expected.iloc[-1]["z"]
    assert rows[0]["date"] == "2025-01-01"
    assert rows[0]["z"] is None
    visible = clip_calendar(pd.DataFrame(rows), 30, end="2025-03-21")
    assert visible.iloc[0]["z"] == expected.iloc[50]["z"]
    json.dumps(result, allow_nan=False)


def test_clip_is_calendar_inclusive_sorted_and_non_mutating():
    frame = pd.DataFrame({"date": ["2025-01-02", "2024-12-31", "2024-12-01"], "v": [3, 2, 1]})
    original = frame.copy(deep=True)
    assert clip_calendar(frame, 3, end="2025-01-01")["v"].tolist() == [2]
    assert clip_calendar(frame, None, end="2025-01-01")["v"].tolist() == [1, 2]
    pd.testing.assert_frame_equal(frame, original)
    with pytest.raises(ValueError):
        clip_calendar(frame, 0, end="2025-01-01")


def correlation(result, period, x, y, lag):
    return next(
        row
        for row in result["periods"][period]["correlations"]
        if (row["x"], row["y"], row["lag"]) == (x, y, lag)
    )


def test_period_correlations_share_latest_day_and_pair_by_calendar():
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-12-01", periods=70),
            "steps": list(range(70)),
            "sleep_minutes": list(range(70)),
            "resting_hr": [60.0] * 70,
        }
    )
    frame.loc[69, "sleep_minutes"] = float("nan")
    result = build_analytics(frame, pd.DataFrame())
    assert result["periods"]["30"]["startDate"] == "2025-01-10"
    assert result["periods"]["30"]["endDate"] == "2025-02-08"
    row = correlation(result, "30", "steps", "sleep_minutes", 1)
    assert row["n"] == 28
    assert row["spearman"] == pytest.approx(1)
    constant = correlation(result, "all", "sleep_minutes", "resting_hr", 0)
    assert constant["n"] == 69
    assert constant["spearman"] is None
    assert constant["reason"] == "constant_series"
    missing = correlation(result, "30", "sleep_minutes", "hrv_rmssd", 0)
    assert missing["n"] == 0
    assert missing["reason"] == "insufficient_pairs"


def test_missing_dates_are_not_zero_and_coverage_includes_year_boundary():
    frame = pd.DataFrame(
        {"date": ["2024-12-30", "2025-01-01", "2025-01-08"], "steps": [10, 30, 50]}
    )
    result = build_analytics(frame, pd.DataFrame())
    assert [row["value"] for row in result["movingAverages"]["steps"]] == [10, 20, 50]
    coverage = result["periods"]["all"]["coverage"]["steps"]
    assert len(coverage) == 10
    assert coverage[1] == {"date": "2024-12-31", "has_data": False}
    assert coverage[2] == {"date": "2025-01-01", "has_data": True}


def sleep_frame():
    return pd.DataFrame(
        [
            {
                "date": "2025-01-02",
                "start_ts": "2025-01-01T23:00:00",
                "end_ts": "2025-01-02T07:00:00",
                "minutes_asleep": 480,
                "is_main": True,
            },
            {
                "date": "2025-01-03",
                "start_ts": "2025-01-02T23:00:00",
                "end_ts": "2025-01-03T07:00:00",
                "minutes_asleep": 480,
                "is_main": True,
            },
            {
                "date": "2025-01-04",
                "start_ts": "2025-01-04T01:00:00",
                "end_ts": "2025-01-04T09:00:00",
                "minutes_asleep": 480,
                "is_main": True,
            },
            {
                "date": "2025-01-05",
                "start_ts": "2025-01-05T01:00:00",
                "end_ts": "2025-01-05T09:00:00",
                "minutes_asleep": 480,
                "is_main": True,
            },
            {
                "date": "2025-01-06",
                "start_ts": "2025-01-06T13:00:00",
                "end_ts": "2025-01-06T14:00:00",
                "minutes_asleep": 60,
                "is_main": False,
            },
        ]
    )


def test_sleep_rhythm_uses_all_saved_sleep_main_only_and_preserves_naps_input():
    sleep = sleep_frame()
    original = sleep.copy(deep=True)
    result = build_analytics(pd.DataFrame(), sleep)
    assert result["socialJetlag"] == {
        "hours": 2.0,
        "scope": "all_saved_sleep",
        "firstDate": "2025-01-02",
        "lastDate": "2025-01-06",
    }
    assert len(result["movingAverages"]["sleep_main_minutes"]) == 4
    assert result["movingAverages"]["sleep_main_minutes"][-1]["value"] == 480
    assert build_analytics(pd.DataFrame(), sleep.iloc[:3])["socialJetlag"]["hours"] is None
    pd.testing.assert_frame_equal(sleep, original)


def test_empty_and_non_finite_inputs_produce_strict_json():
    empty = build_analytics(pd.DataFrame(), pd.DataFrame())
    assert set(empty["periods"]) == {"30", "90", "180", "365", "all"}
    assert empty["periods"]["all"]["endDate"] is None
    frame = pd.DataFrame(
        {"date": ["2025-01-01", "2025-01-02"], "steps": [float("inf"), float("nan")]}
    )
    result = build_analytics(frame, pd.DataFrame())
    assert result["movingAverages"]["steps"][0]["value"] is None
    assert not any(row["has_data"] for row in result["periods"]["all"]["coverage"]["steps"])
    json.dumps(result, allow_nan=False)
