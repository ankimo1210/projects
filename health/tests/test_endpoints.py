"""Contract tests for health.endpoints: request/response shapes and the
14-entry Google Health catalog. Parser stubs (Task 5 scope) are not called
here -- only their presence and NotImplementedError contract are implicit
in Metric construction succeeding.
"""

import json
from datetime import date
from itertools import pairwise
from pathlib import Path

import pytest
from health.endpoints import (
    CATALOG,
    DAILY_ROLLUP,
    KNOWN_DATA_TYPES,
    RECONCILE,
    Metric,
    ParsedRows,
    PayloadError,
    chunk_ranges,
    civil_midnight,
    closed_open_filter,
    daily_rollup_body,
    response_points,
)

FIXTURES = Path(__file__).parent / "fixtures"


def by_name(name: str) -> Metric:
    return next(m for m in CATALOG if m.name == name)


def load_fixture(filename: str) -> dict:
    return json.loads((FIXTURES / filename).read_text())


# -- civil_midnight / daily_rollup_body ---------------------------------------


def test_civil_midnight_nests_date_and_time_with_no_offset():
    got = civil_midnight(date(2026, 7, 1))
    assert got == {"date": {"year": 2026, "month": 7, "day": 1}, "time": {}}
    assert "utcOffsetSeconds" not in got
    assert "utcOffsetSeconds" not in got["date"]
    assert "utcOffsetSeconds" not in got["time"]


def test_daily_rollup_body_end_is_exclusive_next_day():
    body = daily_rollup_body(date(2026, 7, 1), date(2026, 7, 3))
    assert body["range"]["start"] == civil_midnight(date(2026, 7, 1))
    assert body["range"]["end"] == civil_midnight(date(2026, 7, 4))
    assert body["windowSizeDays"] == 1


def test_daily_rollup_body_single_day_end_rolls_to_next_day():
    body = daily_rollup_body(date(2026, 7, 5), date(2026, 7, 5))
    assert body["range"]["end"] == civil_midnight(date(2026, 7, 6))


# -- closed_open_filter --------------------------------------------------------


def test_closed_open_filter_uses_full_path_and_end_plus_one_day():
    got = closed_open_filter("daily_resting_heart_rate.date", date(2026, 7, 1), date(2026, 7, 3))
    assert (
        got
        == 'daily_resting_heart_rate.date >= "2026-07-01" AND daily_resting_heart_rate.date < "2026-07-04"'
    )


def test_closed_open_filter_single_day():
    got = closed_open_filter("sleep.interval.civil_end_time", date(2026, 7, 5), date(2026, 7, 5))
    assert (
        got
        == 'sleep.interval.civil_end_time >= "2026-07-05" AND sleep.interval.civil_end_time < "2026-07-06"'
    )


# -- chunk_ranges ---------------------------------------------------------------


def test_chunk_ranges_no_gap_or_overlap():
    out = chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), 4)
    assert out == [
        (date(2026, 1, 1), date(2026, 1, 4)),
        (date(2026, 1, 5), date(2026, 1, 8)),
        (date(2026, 1, 9), date(2026, 1, 10)),
    ]
    # contiguous: each chunk's start is the day after the previous chunk's end
    for (_, prev_end), (next_start, _) in pairwise(out):
        assert next_start == date.fromordinal(prev_end.toordinal() + 1)


def test_chunk_ranges_single_day():
    assert chunk_ranges(date(2026, 1, 1), date(2026, 1, 1), 30) == [
        (date(2026, 1, 1), date(2026, 1, 1))
    ]


@pytest.mark.parametrize("max_days", [0, -1])
def test_chunk_ranges_invalid_max_days_raises(max_days):
    with pytest.raises(ValueError):
        chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), max_days)


# -- response_points ------------------------------------------------------------


def _dummy_metric(method: str) -> Metric:
    return Metric(
        "dummy", "dummy-type", method, 90, "activity", True, ("dummy",), lambda pages: ParsedRows()
    )


def test_response_points_reads_rollup_data_points_for_daily_rollup():
    metric = _dummy_metric(DAILY_ROLLUP)
    page = {"rollupDataPoints": [{"a": 1}, {"a": 2}]}
    assert response_points(metric, page) == [{"a": 1}, {"a": 2}]


def test_response_points_reads_data_points_for_reconcile():
    metric = _dummy_metric(RECONCILE)
    page = {"dataPoints": [{"a": 1}]}
    assert response_points(metric, page) == [{"a": 1}]


def test_response_points_missing_key_is_empty_list():
    assert response_points(_dummy_metric(DAILY_ROLLUP), {}) == []
    assert response_points(_dummy_metric(RECONCILE), {}) == []


def test_response_points_non_list_raises_payload_error():
    with pytest.raises(PayloadError) as exc:
        response_points(_dummy_metric(RECONCILE), {"dataPoints": "not-a-list"})
    assert exc.value.metric == "dummy"
    assert "dataPoints" in exc.value.detail


def test_response_points_non_list_rollup_raises_payload_error():
    with pytest.raises(PayloadError) as exc:
        response_points(_dummy_metric(DAILY_ROLLUP), {"rollupDataPoints": {"oops": True}})
    assert exc.value.metric == "dummy"


# -- catalog shape ---------------------------------------------------------------


def test_catalog_has_14_unique_names():
    names = [m.name for m in CATALOG]
    assert len(names) == 14
    assert len(names) == len(set(names))


def test_known_data_types_is_superset_of_catalog_data_types():
    for m in CATALOG:
        assert m.data_type in KNOWN_DATA_TYPES, f"{m.name}'s data_type {m.data_type!r} missing"


def test_rollup_metrics_have_no_filter_path():
    for m in CATALOG:
        if m.method == DAILY_ROLLUP:
            assert m.filter_path is None, m.name


def test_rollup_chunk_limits_are_14_or_90_days():
    fourteen_day = {"calories", "active_minutes"}
    for m in CATALOG:
        if m.method != DAILY_ROLLUP:
            continue
        expected = 14 if m.name in fourteen_day else 90
        assert m.max_range_days == expected, m.name


def test_reconcile_filter_paths_are_exact():
    expected = {
        "resting_hr": "daily_resting_heart_rate.date",
        "hrv": "daily_heart_rate_variability.date",
        "spo2": "daily_oxygen_saturation.date",
        "temp_skin": "daily_sleep_temperature_derivations.date",
        "br": "daily_respiratory_rate.date",
        "sleep": "sleep.interval.civil_end_time",
        "intraday_hr": "heart_rate.sample_time.civil_time",
        "intraday_steps": "steps.interval.civil_start_time",
    }
    for name, path in expected.items():
        assert by_name(name).filter_path == path


def test_sleep_page_size_is_25_other_reconcile_metrics_are_1000():
    assert by_name("sleep").page_size == 25
    reconcile_others = [m for m in CATALOG if m.method == RECONCILE and m.name != "sleep"]
    assert reconcile_others  # sanity: there are other reconcile metrics
    for m in reconcile_others:
        assert m.page_size == 1000, m.name


def test_only_two_intraday_metrics_have_full_history_false():
    not_full = [m.name for m in CATALOG if not m.full_history]
    assert sorted(not_full) == ["intraday_hr", "intraday_steps"]


def test_active_minutes_declares_existing_3_series():
    assert by_name("active_minutes").series_names == (
        "minutes_lightly_active",
        "minutes_fairly_active",
        "minutes_very_active",
    )


def test_body_fat_declares_fat_pct_series():
    assert by_name("body_fat").series_names == ("fat_pct",)


def test_daily_rollup_and_reconcile_method_counts():
    rollup = [m for m in CATALOG if m.method == DAILY_ROLLUP]
    reconcile = [m for m in CATALOG if m.method == RECONCILE]
    assert len(rollup) == 6
    assert len(reconcile) == 8


# -- fixtures: shape sanity via response_points --------------------------------

ROLLUP_FIXTURES = [
    "rollup_steps.json",
    "rollup_distance.json",
    "rollup_calories.json",
    "rollup_active_minutes.json",
    "rollup_weight.json",
    "rollup_body_fat.json",
]

RECONCILE_FIXTURES = [
    "daily_resting_hr.json",
    "daily_hrv.json",
    "daily_spo2.json",
    "daily_skin_temperature.json",
    "daily_respiratory_rate.json",
    "sleep_stages.json",
    "sleep_classic.json",
    "intraday_hr.json",
    "intraday_steps.json",
]


@pytest.mark.parametrize("filename", ROLLUP_FIXTURES)
def test_rollup_fixture_parses_via_response_points(filename):
    page = load_fixture(filename)
    points = response_points(_dummy_metric(DAILY_ROLLUP), page)
    assert len(points) >= 1
    for point in points:
        assert "civilStartTime" in point
        assert "civilEndTime" in point


@pytest.mark.parametrize("filename", RECONCILE_FIXTURES)
def test_reconcile_fixture_parses_via_response_points(filename):
    page = load_fixture(filename)
    points = response_points(_dummy_metric(RECONCILE), page)
    assert len(points) >= 1
    for point in points:
        assert "dataPointName" in point


def test_sleep_stages_fixture_has_stages_summary_and_type():
    (point,) = load_fixture("sleep_stages.json")["dataPoints"]
    sleep = point["sleep"]
    assert sleep["type"] == "STAGES"
    assert len(sleep["summary"]["stagesSummary"]) == 4
    # numeric-string fields per contract: minutesAsleep, stagesSummary[].minutes/count
    assert isinstance(sleep["summary"]["minutesAsleep"], str)
    assert isinstance(sleep["summary"]["stagesSummary"][0]["minutes"], str)
    assert isinstance(sleep["summary"]["stagesSummary"][0]["count"], str)


def test_sleep_classic_fixture_has_no_stages_and_classic_type():
    (point,) = load_fixture("sleep_classic.json")["dataPoints"]
    sleep = point["sleep"]
    assert sleep["type"] == "CLASSIC"
    assert sleep["stages"] == []
    assert sleep["summary"]["stagesSummary"] == []
    assert sleep["metadata"]["nap"] is False


def test_rollup_fixture_numeric_string_fields():
    steps_point = load_fixture("rollup_steps.json")["rollupDataPoints"][0]
    assert isinstance(steps_point["steps"]["countSum"], str)
    distance_point = load_fixture("rollup_distance.json")["rollupDataPoints"][0]
    assert isinstance(distance_point["distance"]["millimetersSum"], str)
    active_minutes_point = load_fixture("rollup_active_minutes.json")["rollupDataPoints"][0]
    levels = active_minutes_point["activeMinutes"]["activeMinutesRollupByActivityLevel"]
    assert {lvl["activityLevel"] for lvl in levels} == {"LIGHT", "MODERATE", "VIGOROUS"}
    assert all(isinstance(lvl["activeMinutesSum"], str) for lvl in levels)
    # kcalSum and *Avg fields are numbers, not strings, per the contracts file
    calories_point = load_fixture("rollup_calories.json")["rollupDataPoints"][0]
    assert isinstance(calories_point["totalCalories"]["kcalSum"], (int, float))
    weight_point = load_fixture("rollup_weight.json")["rollupDataPoints"][0]
    assert isinstance(weight_point["weight"]["weightGramsAvg"], (int, float))


def test_reconcile_fixture_numeric_string_fields():
    resting = load_fixture("daily_resting_hr.json")["dataPoints"][0]
    assert isinstance(resting["dailyRestingHeartRate"]["beatsPerMinute"], str)
    hr_point = load_fixture("intraday_hr.json")["dataPoints"][0]
    assert isinstance(hr_point["heartRate"]["beatsPerMinute"], str)
    steps_point = load_fixture("intraday_steps.json")["dataPoints"][0]
    assert isinstance(steps_point["steps"]["count"], str)
