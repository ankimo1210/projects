from datetime import date

from health.endpoints import CATALOG, ParsedRows, chunk_ranges


def by_name(name):
    return next(m for m in CATALOG if m.name == name)


def test_chunk_ranges_splits_inclusive():
    out = chunk_ranges(date(2026, 1, 1), date(2026, 1, 10), 4)
    assert out == [
        (date(2026, 1, 1), date(2026, 1, 4)),
        (date(2026, 1, 5), date(2026, 1, 8)),
        (date(2026, 1, 9), date(2026, 1, 10)),
    ]


def test_chunk_ranges_single_day():
    assert chunk_ranges(date(2026, 1, 1), date(2026, 1, 1), 30) == [
        (date(2026, 1, 1), date(2026, 1, 1))
    ]


def test_catalog_shape():
    names = [m.name for m in CATALOG]
    assert len(names) == len(set(names))
    for m in CATALOG:
        assert m.path.startswith("/")
        if m.kind == "range":
            assert "{start}" in m.path and "{end}" in m.path
        else:
            assert m.kind == "per_day" and "{date}" in m.path and m.max_range_days == 1


def test_parse_steps():
    payload = {"activities-steps": [{"dateTime": "2026-07-01", "value": "8123"}]}
    rows = by_name("steps").parse(payload)
    assert rows.daily == [("steps", "2026-07-01", 8123.0)]
    assert rows.sleep == () and rows.intraday == ()


def test_parse_heart_resting_and_zones():
    payload = {"activities-heart": [{
        "dateTime": "2026-07-01",
        "value": {"restingHeartRate": 62, "heartRateZones": [
            {"name": "Fat Burn", "minutes": 40},
            {"name": "Cardio", "minutes": 12},
        ]},
    }]}
    daily = dict((m, v) for m, d, v in by_name("heart").parse(payload).daily)
    assert daily["resting_hr"] == 62.0
    assert daily["hr_zone_fat_burn_min"] == 40.0
    assert daily["hr_zone_cardio_min"] == 12.0


def test_parse_heart_missing_resting_hr_skipped():
    payload = {"activities-heart": [{"dateTime": "2026-07-01", "value": {"heartRateZones": []}}]}
    metrics = [m for m, d, v in by_name("heart").parse(payload).daily]
    assert "resting_hr" not in metrics


def test_parse_sleep_sessions_and_daily():
    payload = {"sleep": [{
        "logId": 44, "dateOfSleep": "2026-07-01", "startTime": "2026-06-30T23:41:30.000",
        "endTime": "2026-07-01T07:05:30.000", "minutesAsleep": 402, "efficiency": 93,
        "isMainSleep": True,
        "levels": {"summary": {"deep": {"minutes": 80}, "light": {"minutes": 220},
                               "rem": {"minutes": 102}, "wake": {"minutes": 42}}},
    }]}
    rows = by_name("sleep").parse(payload)
    (s,) = rows.sleep
    assert s["log_id"] == 44 and s["minutes_deep"] == 80
    assert s["start_ts"] == "2026-06-30 23:41:30"
    assert rows.daily == [("sleep_minutes", "2026-07-01", 402.0)]


def test_parse_sleep_classic_log_defaults_stages_to_zero():
    payload = {"sleep": [{"logId": 45, "dateOfSleep": "2026-07-02",
                          "startTime": "2026-07-02T01:00:00.000",
                          "endTime": "2026-07-02T07:00:00.000",
                          "minutesAsleep": 330, "efficiency": 90, "isMainSleep": False}]}
    (s,) = by_name("sleep").parse(payload).sleep
    assert s["minutes_deep"] == 0 and s["is_main"] is False
    assert by_name("sleep").parse(payload).daily == []  # non-main sleep: no daily row


def test_parse_spo2_bare_list():
    payload = [{"dateTime": "2026-07-01", "value": {"avg": 96.1, "min": 93.0, "max": 98.4}}]
    daily = dict((m, v) for m, d, v in by_name("spo2").parse(payload).daily)
    assert daily == {"spo2_avg": 96.1, "spo2_min": 93.0, "spo2_max": 98.4}


def test_parse_weight_fat_optional():
    payload = {"weight": [{"date": "2026-07-01", "weight": 72.5, "fat": 21.1},
                          {"date": "2026-07-02", "weight": 72.1}]}
    daily = by_name("weight").parse(payload).daily
    assert ("weight_kg", "2026-07-01", 72.5) in daily
    assert ("fat_pct", "2026-07-01", 21.1) in daily
    assert ("weight_kg", "2026-07-02", 72.1) in daily
    assert not any(m == "fat_pct" and d == "2026-07-02" for m, d, v in daily)


def test_parse_intraday_hr():
    payload = {
        "activities-heart": [{"dateTime": "2026-07-01"}],
        "activities-heart-intraday": {"dataset": [{"time": "00:00:00", "value": 62},
                                                  {"time": "00:01:00", "value": 63}]},
    }
    rows = by_name("intraday_hr").parse(payload)
    assert rows.intraday[0] == ("hr", "2026-07-01 00:00:00", 62.0)
    assert len(rows.intraday) == 2
