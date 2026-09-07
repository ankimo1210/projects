"""Bounded probes exercise the real transport using only synthetic responses."""

import importlib.util
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from health.auth import AuthError
from health.client import HealthClient
from health.probe import run_source_probe
from health.source_catalog import load_sources

_spec = importlib.util.spec_from_file_location(
    "source_probe_fakes", Path(__file__).with_name("fakes.py")
)
_fakes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fakes)
FakeResponse, FakeSession = _fakes.FakeResponse, _fakes.FakeSession


class Auth:
    def access_token(self):
        return "synthetic"

    def refresh(self):
        raise AuthError("expired synthetic token")


def source(key):
    return next(s for s in load_sources() if s.key == key)


def client(*responses):
    return HealthClient(Auth(), session=FakeSession(responses), min_interval_s=0)


def run(tmp_path, transport, keys, cap=20):
    return run_source_probe(transport, tmp_path, [source(k) for k in keys], date(2026, 9, 7), cap)


def bodies(tmp_path, entry):
    return [(tmp_path / item["path"]).read_bytes() for item in entry["responses"]]


def test_raw_error_is_saved_before_parse_and_other_source_continues(tmp_path):
    transport = client(
        FakeResponse(200, content=b"bad json\n"), FakeResponse(200, {"name": "users/me/profile"})
    )
    result = run(tmp_path, transport, ["heart-rate.list", "profile.getProfile"])
    first, second = result["sources"].values()
    assert first["status"] == "failed"
    assert bodies(tmp_path, first) == [b"bad json\n"]
    assert second["status"] == "ok"
    assert result["requests_made"] == 2
    assert "bad json" not in (tmp_path / "manifest.json").read_text()


def test_cap_keeps_unvisited_pending_and_received_page_with_cursor(tmp_path):
    result = run(
        tmp_path,
        client(FakeResponse(200, {"dataPoints": [{"unknown": 1}], "nextPageToken": "next"})),
        ["heart-rate.list", "profile.getProfile"],
        cap=1,
    )
    first, second = result["sources"].values()
    assert first["status"] == "partial"
    assert second["status"] == "pending"
    assert result["stopped_reason"] == "request_cap"
    assert first["requests"][0]["next_page_token"] == "next"
    assert len(bodies(tmp_path, first)) == 1


@pytest.mark.parametrize(
    ("status", "expected", "stopped"),
    [
        (403, "permission_denied", None),
        (429, "rate_limited", "rate_limited"),
        (401, "failed", "auth_error"),
    ],
)
def test_http_failures_preserve_raw_and_stop_only_global_errors(
    tmp_path, status, expected, stopped
):
    raw = b'{"error":{"message":"secret personal detail"}}'
    result = run(
        tmp_path,
        client(FakeResponse(status, content=raw), FakeResponse(200, {})),
        ["profile.getProfile", "settings.getSettings"],
    )
    first, second = result["sources"].values()
    assert first["status"] == expected
    assert result["stopped_reason"] == stopped
    assert bodies(tmp_path, first) == [raw]
    assert second["status"] == ("pending" if stopped else "ok")
    assert "secret personal detail" not in json.dumps(result)


def test_page_one_survives_page_two_failure(tmp_path):
    transport = client(
        FakeResponse(200, {"pairedDevices": [{"name": "device"}], "nextPageToken": "two"}),
        FakeResponse(500, content=b"failed"),
    )
    result = run(tmp_path, transport, ["paired-devices.list"])
    entry = result["sources"]["paired-devices.list"]
    assert entry["status"] == "failed"
    assert entry["data_point_count"] == 1
    assert len(bodies(tmp_path, entry)) == 2


def test_repeated_token_stops_source_without_spending_entire_cap(tmp_path):
    page = {"pairedDevices": [], "nextPageToken": "same"}
    result = run(
        tmp_path, client(FakeResponse(200, page), FakeResponse(200, page)), ["paired-devices.list"]
    )
    entry = result["sources"]["paired-devices.list"]
    assert entry["status"] == "failed"
    assert entry["reason"] == "repeated_page_token"
    assert result["requests_made"] == 2


def test_probe_checks_recent_older_than_thirty_days_and_five_years(tmp_path):
    transport = client(*[FakeResponse(200, {"dataPoints": []}) for _ in range(3)])
    result = run(tmp_path, transport, ["heart-rate.list"])
    entry = result["sources"]["heart-rate.list"]
    assert entry["status"] == "empty"
    assert entry["history_status"] == "unknown_history"
    assert [r["start"] for r in entry["requests"]] == ["2026-09-07", "2026-08-07", "2021-09-06"]
    assert all(" < " in c["params"]["filter"] for c in transport.session.calls)
    assert all(r["status"] == "empty" for r in entry["requests"])


def test_detail_get_uses_observed_names_and_metadata_envelopes(tmp_path):
    name = "users/person/dataTypes/exercise/dataPoints/1234"
    transport = client(
        FakeResponse(200, {"dataPoints": [{"name": name}]}),
        FakeResponse(200, {"dataPoints": []}),
        FakeResponse(200, {"dataPoints": []}),
        FakeResponse(200, {"name": name, "extra": "detail"}),
    )
    result = run(tmp_path, transport, ["exercise.list", "exercise.get"])
    detail = result["sources"]["exercise.get"]
    assert detail["status"] == "ok"
    assert detail["data_point_count"] == 1
    assert transport.session.calls[-1]["url"].endswith("/" + name)


def test_catalog_unavailable_is_visible_without_http_and_raw_runs_never_overwrite(tmp_path):
    first = run(
        tmp_path,
        client(FakeResponse(200, content=b'{"x":1.00}\n')),
        ["profile.getProfile", "moods.unavailable"],
    )
    second = run(tmp_path, client(FakeResponse(200, content=b'{"x":2}\n')), ["profile.getProfile"])
    assert first["sources"]["moods.unavailable"]["status"] == "unsupported"
    old = first["sources"]["profile.getProfile"]
    new = second["sources"]["profile.getProfile"]
    assert bodies(tmp_path, old) == [b'{"x":1.00}\n']
    assert bodies(tmp_path, new) == [b'{"x":2}\n']
    assert old["responses"][0]["path"] != new["responses"][0]["path"]
    for row in (old, new):
        path = tmp_path / row["responses"][0]["path"]
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700


def test_ecg_queries_have_no_invented_end(tmp_path):
    transport = client(*[FakeResponse(200, {}) for _ in range(3)])
    result = run(tmp_path, transport, ["electrocardiogram.list"])
    assert all(r["end"] is None for r in result["sources"]["electrocardiogram.list"]["requests"])
    assert all(" < " not in c["params"]["filter"] for c in transport.session.calls)


def test_wrong_envelope_is_failed_after_raw_preservation(tmp_path):
    result = run(tmp_path, client(FakeResponse(200, {"dataPoints": None})), ["heart-rate.list"])
    entry = result["sources"]["heart-rate.list"]
    assert entry["status"] == "failed"
    assert len(bodies(tmp_path, entry)) == 1


def test_storage_failure_stops_all_requests(tmp_path, monkeypatch):
    import health.probe as probe

    original = probe._write_private_bytes

    def fail_body(path, body):
        if path.suffix == ".bin":
            raise OSError(28, "no space")
        return original(path, body)

    monkeypatch.setattr(probe, "_write_private_bytes", fail_body)
    transport = client(FakeResponse(200, {}))
    result = run(tmp_path, transport, ["profile.getProfile", "settings.getSettings"])
    assert result["stopped_reason"] == "storage_error"
    assert result["sources"]["profile.getProfile"]["status"] == "storage_error"
    assert result["sources"]["settings.getSettings"]["status"] == "pending"
    assert len(transport.session.calls) == 1


def test_report_includes_failures_and_unavailable_without_private_messages(tmp_path):
    messages = []
    run_source_probe(
        client(FakeResponse(403, {"error": {"message": "private upstream text"}})),
        tmp_path,
        [source("profile.getProfile"), source("moods.unavailable")],
        date(2026, 9, 7),
        2,
        report=messages.append,
    )
    assert len(messages) == 2
    assert "permission_denied" in messages[0]
    assert "unsupported" in messages[1]
    assert "private upstream text" not in "".join(messages)


def test_each_raw_response_identifies_exact_request_page(tmp_path):
    transport = client(
        FakeResponse(200, {"pairedDevices": [], "nextPageToken": "two"}),
        FakeResponse(200, {"pairedDevices": []}),
    )
    result = run(tmp_path, transport, ["paired-devices.list"])
    responses = result["sources"]["paired-devices.list"]["responses"]
    assert "pageToken" not in responses[0]["request"]["params"]
    assert responses[1]["request"]["params"]["pageToken"] == "two"
