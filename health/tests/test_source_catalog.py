"""Public source contracts; no live requests or private fixtures."""

import json
from dataclasses import asdict, replace
from datetime import date

import pytest
from health.source_catalog import (
    RequestSpec,
    build_request,
    load_sources,
    source_points,
    with_page_token,
)


def source(data_type, method=None):
    return next(
        s
        for s in load_sources()
        if s.data_type == data_type and (method is None or s.preferred_method == method)
    )


def test_catalog_keeps_current_legacy_and_unavailable_types():
    sources = load_sources()
    assert len({s.key for s in sources}) == len(sources)
    assert source("heart-rate").preferred_method == "list"
    assert source("basal-energy-burned").availability == "unverified"
    for name in ("moods", "symptoms", "ovulation-test", "menstrual-period"):
        s = source(name)
        assert s.availability == "unsupported"
        assert s.preferred_method is None
        assert s.readonly_scopes == ()
    assert source("nutrition-log").readonly_scopes == (
        "https://www.googleapis.com/auth/googlehealth.nutrition.readonly",
    )
    assert source("food").representation == "reference"
    assert source("total-calories").representation == "aggregate"
    assert source("floors").representation == "reconciled"
    assert all(x.endswith(".readonly") for s in sources for x in s.readonly_scopes)
    assert all(s.evidence_url.startswith("https://developers.google.com/") for s in sources)
    assert all(not s.unbounded_verified for s in sources if s.filter_kind != "none")


def test_loader_rejects_write_scope_and_duplicate_keys(tmp_path):
    row = asdict(source("heart-rate"))
    path = tmp_path / "catalog.json"
    row["readonly_scopes"] = ["https://www.googleapis.com/auth/googlehealth.sleep.writeonly"]
    path.write_text(json.dumps([row]))
    with pytest.raises(ValueError, match="readonly"):
        load_sources(path)
    row = asdict(source("heart-rate"))
    path.write_text(json.dumps([row, row]))
    with pytest.raises(ValueError, match="duplicate"):
        load_sources(path)


@pytest.mark.parametrize(
    ("data_type", "field"),
    [
        ("daily-vo2-max", "daily_vo2_max.date"),
        ("run-vo2-max", "run_vo2_max.sample_time.civil_time"),
        ("vo2-max", "vo2_max.sample_time.civil_time"),
    ],
)
def test_vo2_max_uses_official_identifiers_in_paths_and_filters(data_type, field):
    sources = {s.key: s for s in load_sources()}
    assert f"{data_type}.list" in sources
    s = sources[f"{data_type}.list"]
    assert s.data_type == data_type
    assert s.filter_field == field
    request = build_request(s, start=date(2026, 9, 6), end=date(2026, 9, 7))
    assert request.path == f"/v4/users/me/dataTypes/{data_type}/dataPoints"
    assert request.params["filter"] == f'{field} >= "2026-09-06" AND {field} < "2026-09-07"'
    assert not {"daily-vo.list", "run-vo.list", "vo.list"} & sources.keys()


@pytest.mark.parametrize(
    ("name", "field"),
    [
        ("heart-rate", "heart_rate.sample_time.civil_time"),
        ("steps", "steps.interval.civil_start_time"),
        ("daily-heart-rate-variability", "daily_heart_rate_variability.date"),
        ("sleep", "sleep.interval.civil_end_time"),
    ],
)
def test_closed_open_filter(name, field):
    s = source(name)
    req = build_request(s, start=date(2020, 1, 1), end=date(2020, 1, 2))
    assert req == RequestSpec(
        "GET",
        f"/v4/users/me/dataTypes/{name}/dataPoints",
        {"pageSize": s.page_size, "filter": f'{field} >= "2020-01-01" AND {field} < "2020-01-02"'},
        None,
    )
    assert s.range_evidence_url
    with pytest.raises(ValueError, match="unbounded"):
        build_request(s)


def test_ecg_never_fabricates_upper_bound():
    s = source("electrocardiogram")
    req = build_request(s, start=date(2020, 1, 1))
    assert req.params["filter"] == 'electrocardiogram.interval.start_time >= "2020-01-01T00:00:00Z"'
    with pytest.raises(ValueError, match="upper"):
        build_request(s, start=date(2020, 1, 1), end=date(2020, 1, 2))


def test_rollup_range_and_pagination_preserve_body():
    s = source("total-calories")
    req = build_request(s, start=date(2020, 1, 1), end=date(2020, 1, 2))
    assert req.method == "POST"
    assert req.path.endswith(":dailyRollUp")
    assert req.body["range"]["end"]["date"] == {"year": 2020, "month": 1, "day": 2}
    paged = with_page_token(req, "next")
    assert paged.body["pageToken"] == "next"
    assert "pageToken" not in req.body
    with pytest.raises(ValueError, match="range"):
        build_request(s, start=date(2020, 1, 1), end=date(2020, 2, 1))


@pytest.mark.parametrize("data_type", ["total-calories", "calories-in-heart-rate-zone"])
def test_rollup_uses_explicit_midnight_and_default_page_size(data_type):
    request = build_request(source(data_type), start=date(2026, 9, 6), end=date(2026, 9, 7))
    assert request.body == {
        "range": {
            "start": {"date": {"year": 2026, "month": 9, "day": 6}, "time": {}},
            "end": {"date": {"year": 2026, "month": 9, "day": 7}, "time": {}},
        },
        "windowSizeDays": 1,
    }
    paged = with_page_token(request, "next")
    assert paged.body == {**request.body, "pageToken": "next"}
    assert "pageToken" not in request.body


def test_metadata_and_detail_paths_are_explicit_and_validated():
    profile = source("profile")
    assert build_request(profile) == RequestSpec("GET", "/v4/users/me/profile", {}, None)
    devices = source("paired-devices", "list")
    assert build_request(devices).params == {"pageSize": 100}
    assert source_points(devices, {"pairedDevices": [{"name": "x"}]}) == [{"name": "x"}]
    detail = source("exercise", "get")
    assert detail.detail_parent == source("exercise", "list").key
    name = "users/abc-123/dataTypes/exercise/dataPoints/1234"
    assert build_request(detail, resource_name=name).path == "/v4/" + name
    for invalid in (
        "https://evil.test/x",
        "users/me/dataTypes/sleep/dataPoints/abcd",
        "users/me/dataTypes/exercise/dataPoints/../profile",
        "users/me/dataTypes/exercise/dataPoints/a?x=y",
    ):
        with pytest.raises(ValueError):
            build_request(detail, resource_name=invalid)
    with pytest.raises(ValueError, match="resource_name"):
        build_request(detail)


def test_bad_envelope_is_not_empty_and_missing_proto_repeated_field_is_empty():
    s = source("heart-rate")
    assert source_points(s, {}) == []
    for payload in (None, [], {"dataPoints": None}, {"dataPoints": {}}, {"dataPoints": [1]}):
        with pytest.raises(ValueError):
            source_points(s, payload)
    assert source_points(source("profile"), {"name": "users/me/profile"}) == [
        {"name": "users/me/profile"}
    ]


def test_unavailable_source_cannot_build_request():
    with pytest.raises(ValueError, match="unavailable"):
        build_request(source("moods"))
    s = replace(source("heart-rate"), max_range_days=1)
    with pytest.raises(ValueError, match="range"):
        build_request(s, start=date(2020, 1, 1), end=date(2020, 1, 3))


def test_explicit_unverified_listing_can_fetch_without_claiming_history():
    s = source("heart-rate")
    req = build_request(s, allow_unverified_unbounded=True)
    assert req.params == {"pageSize": s.page_size}
    assert s.unbounded_verified is False
    with pytest.raises(ValueError, match="range"):
        build_request(source("total-calories"), allow_unverified_unbounded=True)
