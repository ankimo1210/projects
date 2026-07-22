"""Contract tests for health.endpoints: request/response shapes, the 14-entry
Google Health catalog, and the typed parsers for all 14 catalog entries
(Task 5)."""

import json
from datetime import date, datetime
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
    parse_active_minutes_rollup,
    parse_body_fat_rollup,
    parse_br_reconcile,
    parse_calories_rollup,
    parse_distance_rollup,
    parse_hrv_reconcile,
    parse_intraday_hr_reconcile,
    parse_intraday_steps_reconcile,
    parse_resting_hr_reconcile,
    parse_sleep_reconcile,
    parse_spo2_reconcile,
    parse_steps_rollup,
    parse_temp_skin_reconcile,
    parse_weight_rollup,
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


# -- scope: must be one of the 3 OAuth scopes auth.py actually requests --------

REQUESTED_SCOPES = {"activity_and_fitness", "health_metrics_and_measurements", "sleep"}


def test_catalog_scope_is_one_of_requested_oauth_scopes():
    for m in CATALOG:
        assert m.scope in REQUESTED_SCOPES, f"{m.name}: unexpected scope {m.scope!r}"


def test_catalog_scope_spot_values():
    assert by_name("steps").scope == "activity_and_fitness"
    assert by_name("weight").scope == "health_metrics_and_measurements"
    assert by_name("sleep").scope == "sleep"


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


# ===============================================================================
# Task 5: typed parsers
# ===============================================================================

# -- small synthetic-page builders (fixtures are fixed; edge cases need ad hoc
# pages that the committed fixtures don't and shouldn't encode) ----------------


def _civil(y, m, d, h=0, mi=0, s=0) -> dict:
    return {
        "date": {"year": y, "month": m, "day": d},
        "time": {"hours": h, "minutes": mi, "seconds": s},
    }


def _rollup_page(points: list[dict]) -> dict:
    return {"rollupDataPoints": points}


def _reconcile_page(points: list[dict]) -> dict:
    return {"dataPoints": points}


def _daily(name: str, d: date, value: float) -> tuple:
    return (name, d, value)


def daily_as_dict(rows) -> dict:
    """(name, date, value) rows -> {(name, date): value} for order-independent asserts."""
    return {(n, d): v for n, d, v in rows}


def intraday_as_dict(rows) -> dict:
    return {(n, ts): v for n, ts, v in rows}


# -- rollup parsers ---------------------------------------------------------------


def test_parse_steps_rollup_reads_countsum_keyed_by_civil_start_date():
    page = load_fixture("rollup_steps.json")
    got = daily_as_dict(parse_steps_rollup([page]).daily)
    assert got == {
        ("steps", date(2026, 7, 1)): 8000.0,
        ("steps", date(2026, 7, 2)): 9000.0,
    }


def test_parse_distance_rollup_converts_millimeters_to_km():
    page = load_fixture("rollup_distance.json")
    got = daily_as_dict(parse_distance_rollup([page]).daily)
    assert got == {
        ("distance_km", date(2026, 7, 1)): 5.0,
        ("distance_km", date(2026, 7, 2)): 6.2,
    }


def test_parse_calories_rollup_reads_kcal_sum():
    page = load_fixture("rollup_calories.json")
    got = daily_as_dict(parse_calories_rollup([page]).daily)
    assert got == {
        ("calories", date(2026, 7, 1)): 2200.0,
        ("calories", date(2026, 7, 2)): 2350.0,
    }


def test_parse_active_minutes_rollup_maps_light_moderate_vigorous():
    page = load_fixture("rollup_active_minutes.json")
    got = daily_as_dict(parse_active_minutes_rollup([page]).daily)
    d = date(2026, 7, 1)
    assert got == {
        ("minutes_lightly_active", d): 120.0,
        ("minutes_fairly_active", d): 30.0,
        ("minutes_very_active", d): 15.0,
    }


def test_parse_active_minutes_rollup_missing_level_produces_no_row():
    point = {
        "civilStartTime": _civil(2026, 7, 1),
        "civilEndTime": _civil(2026, 7, 2),
        "activeMinutes": {
            "activeMinutesRollupByActivityLevel": [
                {"activeMinutesSum": "45", "activityLevel": "LIGHT"},
            ]
        },
    }
    got = daily_as_dict(parse_active_minutes_rollup([_rollup_page([point])]).daily)
    assert got == {("minutes_lightly_active", date(2026, 7, 1)): 45.0}
    assert ("minutes_fairly_active", date(2026, 7, 1)) not in got
    assert ("minutes_very_active", date(2026, 7, 1)) not in got


def test_parse_active_minutes_rollup_explicit_zero_is_a_zero_row_not_skipped():
    point = {
        "civilStartTime": _civil(2026, 7, 1),
        "civilEndTime": _civil(2026, 7, 2),
        "activeMinutes": {
            "activeMinutesRollupByActivityLevel": [
                {"activeMinutesSum": "0", "activityLevel": "MODERATE"},
            ]
        },
    }
    got = daily_as_dict(parse_active_minutes_rollup([_rollup_page([point])]).daily)
    assert got == {("minutes_fairly_active", date(2026, 7, 1)): 0.0}


def test_parse_weight_rollup_converts_grams_to_kg():
    page = load_fixture("rollup_weight.json")
    got = daily_as_dict(parse_weight_rollup([page]).daily)
    assert got == {("weight_kg", date(2026, 7, 1)): 72.5}


def test_parse_body_fat_rollup_reads_percentage():
    page = load_fixture("rollup_body_fat.json")
    got = daily_as_dict(parse_body_fat_rollup([page]).daily)
    assert got == {("fat_pct", date(2026, 7, 1)): 21.5}


def test_rollup_row_date_is_civil_start_time_not_civil_end_time():
    # civilStartTime and civilEndTime are on different days (windowSizeDays=1);
    # the row must land on the start day.
    page = load_fixture("rollup_steps.json")
    (row,) = [r for r in parse_steps_rollup([page]).daily if r[1] == date(2026, 7, 1)]
    assert row == ("steps", date(2026, 7, 1), 8000.0)


# -- shared behavior: required vs optional fields, duplicates, zero values -----


def test_rollup_missing_civil_start_time_raises_payload_error():
    point = {"civilEndTime": _civil(2026, 7, 2), "steps": {"countSum": "100"}}
    with pytest.raises(PayloadError) as exc:
        parse_steps_rollup([_rollup_page([point])])
    assert exc.value.metric == "steps"
    assert "civilStartTime" in exc.value.detail


def test_rollup_duplicate_series_date_across_pages_raises_payload_error():
    point = {
        "civilStartTime": _civil(2026, 7, 1),
        "civilEndTime": _civil(2026, 7, 2),
        "steps": {"countSum": "100"},
    }
    page1 = _rollup_page([point])
    page2 = _rollup_page([point])
    with pytest.raises(PayloadError) as exc:
        parse_steps_rollup([page1, page2])
    assert exc.value.metric == "steps"


def test_rollup_missing_value_object_is_skipped_not_an_error():
    point = {"civilStartTime": _civil(2026, 7, 1), "civilEndTime": _civil(2026, 7, 2)}
    got = parse_steps_rollup([_rollup_page([point])]).daily
    assert got == ()


def test_rollup_zero_value_is_preserved_not_skipped():
    point = {
        "civilStartTime": _civil(2026, 7, 1),
        "civilEndTime": _civil(2026, 7, 2),
        "steps": {"countSum": "0"},
    }
    got = daily_as_dict(parse_steps_rollup([_rollup_page([point])]).daily)
    assert got == {("steps", date(2026, 7, 1)): 0.0}


def test_reconcile_unrelated_data_point_is_skipped_not_an_error():
    # a dataPoint that doesn't carry this metric's own union field is simply
    # not relevant to this parser.
    point = {"dataPointName": "x", "weight": {"weightGramsAvg": 70000}}
    got = parse_resting_hr_reconcile([_reconcile_page([point])]).daily
    assert got == ()


def test_reconcile_missing_date_field_raises_payload_error():
    point = {
        "dataPointName": "x",
        "dailyRestingHeartRate": {"beatsPerMinute": "60"},
    }
    with pytest.raises(PayloadError) as exc:
        parse_resting_hr_reconcile([_reconcile_page([point])])
    assert exc.value.metric == "resting_hr"
    assert "date" in exc.value.detail


# -- daily reconcile parsers -------------------------------------------------------


def test_parse_resting_hr_reconcile_reads_beats_per_minute():
    page = load_fixture("daily_resting_hr.json")
    got = daily_as_dict(parse_resting_hr_reconcile([page]).daily)
    assert got == {
        ("resting_hr", date(2026, 7, 1)): 58.0,
        ("resting_hr", date(2026, 7, 2)): 60.0,
    }


def test_parse_hrv_reconcile_reads_average_and_deep_rmssd_as_two_series():
    page = load_fixture("daily_hrv.json")
    got = daily_as_dict(parse_hrv_reconcile([page]).daily)
    d = date(2026, 7, 1)
    assert got == {("hrv_rmssd", d): 45.2, ("hrv_deep_rmssd", d): 38.7}


def test_parse_hrv_reconcile_deep_rmssd_independently_optional():
    point = {
        "dataPointName": "x",
        "dailyHeartRateVariability": {
            "averageHeartRateVariabilityMilliseconds": 40.0,
            "date": {"year": 2026, "month": 7, "day": 1},
            # deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds absent
        },
    }
    got = daily_as_dict(parse_hrv_reconcile([_reconcile_page([point])]).daily)
    d = date(2026, 7, 1)
    assert got == {("hrv_rmssd", d): 40.0}
    assert ("hrv_deep_rmssd", d) not in got


def test_parse_spo2_reconcile_reads_average_lower_upper():
    page = load_fixture("daily_spo2.json")
    got = daily_as_dict(parse_spo2_reconcile([page]).daily)
    d = date(2026, 7, 1)
    assert got == {
        ("spo2_avg", d): 96.5,
        ("spo2_lower_bound", d): 93.0,
        ("spo2_upper_bound", d): 98.0,
    }


def test_parse_temp_skin_reconcile_computes_nightly_minus_baseline():
    page = load_fixture("daily_skin_temperature.json")
    got = daily_as_dict(parse_temp_skin_reconcile([page]).daily)
    d = date(2026, 7, 1)
    assert set(got) == {("temp_skin_relative", d)}
    assert got[("temp_skin_relative", d)] == pytest.approx(0.3)


def test_parse_temp_skin_reconcile_skips_when_baseline_missing():
    point = {
        "dataPointName": "x",
        "dailySleepTemperatureDerivations": {
            "date": {"year": 2026, "month": 7, "day": 1},
            "nightlyTemperatureCelsius": 36.3,
            "relativeNightlyStddev30dCelsius": 0.2,
            # baselineTemperatureCelsius absent
        },
    }
    got = parse_temp_skin_reconcile([_reconcile_page([point])]).daily
    assert got == ()


def test_parse_temp_skin_reconcile_never_substitutes_relative_stddev():
    # Same fixture as above, but assert the value isn't the stddev (0.2) --
    # it must be nightly - baseline (~0.3), never relativeNightlyStddev30dCelsius.
    page = load_fixture("daily_skin_temperature.json")
    (value,) = daily_as_dict(parse_temp_skin_reconcile([page]).daily).values()
    assert value != pytest.approx(0.2)


def test_parse_br_reconcile_reads_breaths_per_minute():
    page = load_fixture("daily_respiratory_rate.json")
    got = daily_as_dict(parse_br_reconcile([page]).daily)
    assert got == {("breathing_rate", date(2026, 7, 1)): 14.5}


# -- sleep parser -------------------------------------------------------------------


def _sleep_point(
    provider_id: str,
    *,
    start_civil: dict | None,
    end_civil: dict | None,
    minutes_asleep: str,
    minutes_in_period: str,
    stages_summary: list[dict],
    nap: bool = False,
    start_time: str | None = None,
    start_offset: str | None = None,
    end_time: str | None = None,
    end_offset: str | None = None,
    minutes_awake: str | None = None,
    sleep_type: str = "STAGES",
) -> dict:
    interval: dict = {}
    if start_civil is not None:
        interval["civilStartTime"] = start_civil
    if end_civil is not None:
        interval["civilEndTime"] = end_civil
    if start_time is not None:
        interval["startTime"] = start_time
    if start_offset is not None:
        interval["startUtcOffset"] = start_offset
    if end_time is not None:
        interval["endTime"] = end_time
    if end_offset is not None:
        interval["endUtcOffset"] = end_offset
    summary = {
        "minutesAsleep": minutes_asleep,
        "minutesInSleepPeriod": minutes_in_period,
        "stagesSummary": stages_summary,
    }
    if minutes_awake is not None:
        summary["minutesAwake"] = minutes_awake
    return {
        "dataPointName": provider_id,
        "sleep": {
            "interval": interval,
            "metadata": {"nap": nap},
            "summary": summary,
            "type": sleep_type,
        },
    }


def test_parse_sleep_reconcile_stages_fixture_full_row():
    page = load_fixture("sleep_stages.json")
    (row,) = parse_sleep_reconcile([page]).sleep
    assert row["provider_id"] == "users/me/dataTypes/sleep/dataPoints/fake-sleep-stages-1"
    assert row["date"] == date(2026, 7, 2)
    assert row["start_ts"] == datetime(2026, 7, 1, 23, 30, 0)
    assert row["end_ts"] == datetime(2026, 7, 2, 7, 0, 0)
    assert row["minutes_asleep"] == 420
    assert row["minutes_deep"] == 80
    assert row["minutes_light"] == 220
    assert row["minutes_rem"] == 100
    assert row["minutes_wake"] == 20
    assert row["efficiency"] == round(420 / 450 * 100)
    assert row["is_main"] is True


def test_parse_sleep_reconcile_classic_fixture_zero_stages():
    page = load_fixture("sleep_classic.json")
    (row,) = parse_sleep_reconcile([page]).sleep
    assert row["provider_id"] == "users/me/dataTypes/sleep/dataPoints/fake-sleep-classic-1"
    assert row["date"] == date(2026, 7, 3)
    assert row["minutes_asleep"] == 390
    assert row["minutes_deep"] == 0
    assert row["minutes_light"] == 0
    assert row["minutes_rem"] == 0
    assert row["minutes_wake"] == 20  # fallback to summary.minutesAwake
    assert row["efficiency"] == round(390 / 410 * 100)
    assert row["is_main"] is True


def test_parse_sleep_reconcile_uuid_data_point_name_preserved_verbatim():
    page = load_fixture("sleep_stages.json")
    expected = page["dataPoints"][0]["dataPointName"]
    (row,) = parse_sleep_reconcile([page]).sleep
    assert row["provider_id"] == expected


def test_parse_sleep_reconcile_main_session_is_longest_non_nap():
    points = [
        _sleep_point(
            "nap-1",
            start_civil=_civil(2026, 7, 1, 13, 0),
            end_civil=_civil(2026, 7, 1, 15, 0),
            minutes_asleep="110",
            minutes_in_period="120",
            stages_summary=[],
            nap=True,
        ),
        _sleep_point(
            "main-1",
            start_civil=_civil(2026, 6, 30, 23, 0),
            end_civil=_civil(2026, 7, 1, 6, 0),
            minutes_asleep="380",
            minutes_in_period="420",
            stages_summary=[],
            nap=False,
        ),
    ]
    rows = {r["provider_id"]: r for r in parse_sleep_reconcile([_reconcile_page(points)]).sleep}
    assert rows["nap-1"]["is_main"] is False
    assert rows["main-1"]["is_main"] is True


def test_parse_sleep_reconcile_all_naps_longest_wins():
    points = [
        _sleep_point(
            "nap-short",
            start_civil=_civil(2026, 7, 1, 13, 0),
            end_civil=_civil(2026, 7, 1, 13, 30),
            minutes_asleep="25",
            minutes_in_period="30",
            stages_summary=[],
            nap=True,
        ),
        _sleep_point(
            "nap-long",
            start_civil=_civil(2026, 7, 1, 15, 0),
            end_civil=_civil(2026, 7, 1, 16, 0),
            minutes_asleep="55",
            minutes_in_period="60",
            stages_summary=[],
            nap=True,
        ),
    ]
    rows = {r["provider_id"]: r for r in parse_sleep_reconcile([_reconcile_page(points)]).sleep}
    assert rows["nap-short"]["is_main"] is False
    assert rows["nap-long"]["is_main"] is True


def test_parse_sleep_reconcile_classic_type_alone_does_not_zero_stages():
    # deep/light/rem come from stagesSummary being empty, not from checking
    # sleep.type == "CLASSIC" -- a STAGES-typed point with real stage data
    # must still get non-zero deep/light/rem regardless of `type`.
    point = _sleep_point(
        "s1",
        start_civil=_civil(2026, 7, 1, 23, 0),
        end_civil=_civil(2026, 7, 2, 6, 0),
        minutes_asleep="300",
        minutes_in_period="320",
        stages_summary=[
            {"count": "1", "minutes": "50", "type": "DEEP"},
            {"count": "1", "minutes": "200", "type": "LIGHT"},
            {"count": "1", "minutes": "50", "type": "REM"},
            {"count": "1", "minutes": "20", "type": "AWAKE"},
        ],
        sleep_type="STAGES",
    )
    (row,) = parse_sleep_reconcile([_reconcile_page([point])]).sleep
    assert (row["minutes_deep"], row["minutes_light"], row["minutes_rem"]) == (50, 200, 50)


def test_parse_sleep_reconcile_physical_time_fallback_when_civil_absent():
    point = _sleep_point(
        "s1",
        start_civil=None,
        end_civil=None,
        start_time="2026-07-01T14:00:00Z",
        start_offset="32400s",
        end_time="2026-07-01T21:30:00Z",
        end_offset="32400s",
        minutes_asleep="60",
        minutes_in_period="90",
        stages_summary=[],
    )
    (row,) = parse_sleep_reconcile([_reconcile_page([point])]).sleep
    # UTC 14:00 + 32400s (9h) offset -> local 23:00
    assert row["start_ts"] == datetime(2026, 7, 1, 23, 0, 0)
    # UTC 21:30 + 9h -> local 06:30 next day
    assert row["end_ts"] == datetime(2026, 7, 2, 6, 30, 0)
    assert row["date"] == date(2026, 7, 2)


def test_parse_sleep_reconcile_cross_midnight_session_date_and_times():
    point = _sleep_point(
        "s1",
        start_civil=_civil(2026, 7, 1, 23, 15),
        end_civil=_civil(2026, 7, 2, 6, 45),
        minutes_asleep="400",
        minutes_in_period="450",
        stages_summary=[],
    )
    (row,) = parse_sleep_reconcile([_reconcile_page([point])]).sleep
    assert row["start_ts"] == datetime(2026, 7, 1, 23, 15, 0)
    assert row["end_ts"] == datetime(2026, 7, 2, 6, 45, 0)
    # wake day is the end (civilEndTime) date, not the start date
    assert row["date"] == date(2026, 7, 2)


def test_parse_sleep_reconcile_duplicate_provider_id_raises_payload_error():
    point = _sleep_point(
        "dup-1",
        start_civil=_civil(2026, 7, 1, 23, 0),
        end_civil=_civil(2026, 7, 2, 6, 0),
        minutes_asleep="300",
        minutes_in_period="330",
        stages_summary=[],
    )
    page1 = _reconcile_page([point])
    page2 = _reconcile_page([point])
    with pytest.raises(PayloadError) as exc:
        parse_sleep_reconcile([page1, page2])
    assert exc.value.metric == "sleep"


def test_parse_sleep_reconcile_missing_minutes_asleep_raises_payload_error():
    point = {
        "dataPointName": "s1",
        "sleep": {
            "interval": {
                "civilStartTime": _civil(2026, 7, 1, 23, 0),
                "civilEndTime": _civil(2026, 7, 2, 6, 0),
            },
            "metadata": {"nap": False},
            "summary": {"minutesInSleepPeriod": "300", "stagesSummary": []},
            "type": "STAGES",
        },
    }
    with pytest.raises(PayloadError) as exc:
        parse_sleep_reconcile([_reconcile_page([point])])
    assert exc.value.metric == "sleep"


def test_parse_sleep_reconcile_missing_start_and_end_time_raises_payload_error():
    point = {
        "dataPointName": "s1",
        "sleep": {
            "interval": {},  # no civil, no physical fallback at all
            "metadata": {"nap": False},
            "summary": {"minutesAsleep": "300", "minutesInSleepPeriod": "330", "stagesSummary": []},
            "type": "STAGES",
        },
    }
    with pytest.raises(PayloadError) as exc:
        parse_sleep_reconcile([_reconcile_page([point])])
    assert exc.value.metric == "sleep"


# -- intraday parsers ---------------------------------------------------------------


def test_parse_intraday_hr_reconcile_reads_civil_sample_time_and_bpm():
    page = load_fixture("intraday_hr.json")
    got = intraday_as_dict(parse_intraday_hr_reconcile([page]).intraday)
    assert got == {
        ("hr", datetime(2026, 7, 1, 0, 1, 0)): 63.0,
        ("hr", datetime(2026, 7, 1, 0, 2, 0)): 65.0,
    }


def test_parse_intraday_steps_reconcile_reads_civil_interval_start_and_count():
    page = load_fixture("intraday_steps.json")
    got = intraday_as_dict(parse_intraday_steps_reconcile([page]).intraday)
    assert got == {("steps", datetime(2026, 7, 1, 0, 0, 0)): 12.0}


def test_parse_intraday_hr_reconcile_physical_time_fallback():
    point = {
        "dataPointName": "hr-1",
        "heartRate": {
            "beatsPerMinute": "70",
            "sampleTime": {
                "physicalTime": "2026-07-01T00:05:00Z",
                "utcOffset": "32400s",
            },
        },
    }
    got = intraday_as_dict(parse_intraday_hr_reconcile([_reconcile_page([point])]).intraday)
    assert got == {("hr", datetime(2026, 7, 1, 9, 5, 0)): 70.0}


def test_parse_intraday_hr_reconcile_multi_page_merge_is_order_independent():
    page = load_fixture("intraday_hr.json")
    points = page["dataPoints"]
    forward = parse_intraday_hr_reconcile(
        [_reconcile_page([points[0]]), _reconcile_page([points[1]])]
    ).intraday
    backward = parse_intraday_hr_reconcile(
        [_reconcile_page([points[1]]), _reconcile_page([points[0]])]
    ).intraday
    assert set(forward) == set(backward)
    assert len(forward) == 2


def test_parse_intraday_hr_reconcile_duplicate_timestamp_raises_payload_error():
    point = load_fixture("intraday_hr.json")["dataPoints"][0]
    with pytest.raises(PayloadError) as exc:
        parse_intraday_hr_reconcile([_reconcile_page([point]), _reconcile_page([point])])
    assert exc.value.metric == "intraday_hr"


def test_parse_intraday_steps_reconcile_duplicate_timestamp_raises_payload_error():
    point = load_fixture("intraday_steps.json")["dataPoints"][0]
    with pytest.raises(PayloadError) as exc:
        parse_intraday_steps_reconcile([_reconcile_page([point]), _reconcile_page([point])])
    assert exc.value.metric == "intraday_steps"


def test_parse_intraday_hr_reconcile_missing_bpm_skips_row_not_an_error():
    point = {
        "dataPointName": "hr-1",
        "heartRate": {
            "sampleTime": {"civilTime": {"date": {"year": 2026, "month": 7, "day": 1}, "time": {}}},
        },
    }
    got = parse_intraday_hr_reconcile([_reconcile_page([point])]).intraday
    assert got == ()


def test_parse_intraday_hr_reconcile_missing_sample_time_raises_payload_error():
    point = {"dataPointName": "hr-1", "heartRate": {"beatsPerMinute": "70", "sampleTime": {}}}
    with pytest.raises(PayloadError) as exc:
        parse_intraday_hr_reconcile([_reconcile_page([point])])
    assert exc.value.metric == "intraday_hr"


def test_sleep_reconcile_emits_daily_sleep_minutes_per_wake_date():
    pages = [load_fixture("sleep_stages.json"), load_fixture("sleep_classic.json")]
    parsed = parse_sleep_reconcile(pages)
    assert parsed.daily == (
        ("sleep_minutes", date(2026, 7, 2), 420.0),
        ("sleep_minutes", date(2026, 7, 3), 390.0),
    )


def test_sleep_reconcile_daily_minutes_sum_all_sessions_of_a_date():
    page = load_fixture("sleep_stages.json")
    nap = json.loads(json.dumps(page))  # deep copy, same wake date as the main session
    point = nap["dataPoints"][0]
    point["dataPointName"] = "users/me/dataTypes/sleep/dataPoints/fake-nap-1"
    point["sleep"]["summary"]["minutesAsleep"] = "45"
    point["sleep"]["metadata"] = {"nap": True}
    parsed = parse_sleep_reconcile([page, nap])
    assert parsed.daily == (("sleep_minutes", date(2026, 7, 2), 465.0),)
