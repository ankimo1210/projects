"""Synthetic Health Planet responses: lossless storage and bounded resumption."""

import json
from datetime import date

import pytest

from health import healthplanet as hp


class Auth:
    def access_token(self):
        return "SYNTHETIC_SECRET"


class Response:
    def __init__(self, body, status=200):
        self.content = body
        self.status_code = status
        self.headers = {}


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


def payload(*items):
    return json.dumps({"data": items, "unknown": "KEEP_RAW_ONLY"}).encode()


def measure(time="202609070700", tag="6021", value="60.25", model="01000000"):
    return {"date": time, "tag": tag, "keydata": value, "model": model}


def run(tmp_path, responses, **kwargs):
    session = Session(responses)
    result = hp.sync(
        tmp_path,
        Auth(),
        start=date(2026, 9, 1),
        end=date(2026, 9, 7),
        session=session,
        clock=lambda: 1788800000,
        **kwargs,
    )
    return result, session


def test_chunks_cover_leap_days_inclusive_and_stay_under_three_months():
    chunks = hp.month_windows(date(2024, 1, 31), date(2024, 4, 2))
    assert chunks == [
        ("20240201000000", "20240402235959"),
        ("20240131000000", "20240131235959"),
    ]
    with pytest.raises(ValueError):
        hp.month_windows(date(2026, 9, 8), date(2026, 9, 7))


def test_sync_can_download_only_innerscan_measurements(tmp_path):
    result, session = run(
        tmp_path,
        [Response(payload(measure()))],
        max_requests=1,
        endpoints=("innerscan",),
    )

    assert result["status"] == "available"
    assert result["remaining_windows"] == 0
    assert [call[0] for call in session.calls] == [
        "https://www.healthplanet.jp/status/innerscan.json"
    ]


def test_raw_bytes_all_daily_measurements_duplicates_and_unknowns_survive(tmp_path):
    body = payload(measure(), measure(), measure("202609072000", value="61"), measure(tag="9999"))
    result, session = run(tmp_path, [Response(body)], max_requests=1)
    assert result["requests_made"] == 1
    assert result["remaining_windows"] == 2
    data = hp.export_data(tmp_path)
    assert len(data["measurements"]) == 3
    assert len({row["id"] for row in data["measurements"]}) == 3
    assert data["quality"]["unparsedRecords"] == 1
    assert data["historyComplete"] is False
    assert "KEEP_RAW_ONLY" not in json.dumps(data)
    assert "SYNTHETIC_SECRET" not in json.dumps(data)
    refs = list((tmp_path / "healthplanet" / "archive" / "objects").glob("*.gz"))
    import gzip

    assert gzip.decompress(refs[0].read_bytes()) == body
    url, kwargs = session.calls[0]
    assert url == "https://www.healthplanet.jp/status/innerscan.json"
    assert kwargs["data"]["date"] == "1"
    assert kwargs["data"]["access_token"] == "SYNTHETIC_SECRET"
    assert kwargs["allow_redirects"] is False
    assert "?" not in url


def test_resume_and_rescan_are_idempotent_with_full_measurement_history(tmp_path):
    run(tmp_path, [Response(payload(measure()))], max_requests=1)
    result, session = run(tmp_path, [Response(payload()), Response(payload())], max_requests=3)
    assert result["requests_made"] == 2
    assert result["remaining_windows"] == 0
    assert "innerscan" not in session.calls[0][0]
    run(
        tmp_path,
        [Response(payload(measure())), Response(payload()), Response(payload())],
        rescan=True,
    )
    assert len(hp.export_data(tmp_path)["measurements"]) == 1


@pytest.mark.parametrize(
    "body,status", [(b"not json", 200), (b'{"error":"bad"}', 200), (b"denied", 403)]
)
def test_failures_archived_without_marking_range_successful(tmp_path, body, status):
    run(tmp_path, [Response(body, status)], max_requests=1)
    source = hp.export_data(tmp_path)["sources"][0]
    assert source["status"] == ("permission_denied" if status == 403 else "failed")
    assert source["intervals"] == []
    assert source["stored_pages"] == 1
    assert not source["history_complete"]


def test_rate_limit_persists_across_runs_and_counts_failed_sends(tmp_path):
    result, _ = run(tmp_path, [Response(b"slow down", 429)], max_requests=3)
    assert result["stopped_reason"] == "rate_limited"
    result, session = run(tmp_path, [], max_requests=3)
    assert session.calls == []
    assert result["stopped_reason"] == "rate_limited"


def test_http_cap_is_shared_across_endpoints_and_invocations(tmp_path):
    for _ in range(20):
        run(tmp_path, [Response(payload()) for _ in range(3)], max_requests=3, rescan=True)
    result, session = run(tmp_path, [], max_requests=3, rescan=True)
    assert result["requests_made"] == 0
    assert result["stopped_reason"] == "rate_limited"
    assert not session.calls


def test_no_configuration_snapshot_is_readonly_and_explicit(tmp_path):
    data = hp.export_data(tmp_path)
    assert data["status"] == "not_connected"
    assert data["measurements"] == []
    assert len(data["sources"]) == 3
    assert all(row["status"] == "pending" for row in data["sources"])
    assert any(row["metric"] == "muscle_mass_kg" for row in data["unsupported"])
    assert not (tmp_path / "healthplanet").exists()


def test_saved_store_does_not_contain_credentials_and_is_private(tmp_path):
    run(tmp_path, [Response(payload(measure()))], max_requests=1)
    path = tmp_path / "healthplanet" / "healthplanet.sqlite3"
    assert path.stat().st_mode & 0o777 == 0o600
    assert b"SYNTHETIC_SECRET" not in path.read_bytes()


def test_second_writer_is_rejected_before_sending(tmp_path):
    import fcntl

    folder = tmp_path / "healthplanet"
    folder.mkdir()
    with (folder / "sync.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            run(tmp_path, [], max_requests=1)


def test_failed_database_initialization_can_be_retried(tmp_path, monkeypatch):
    connect = hp.sqlite3.connect

    def fail(*args, **kwargs):
        raise hp.sqlite3.OperationalError("temporary initialization failure")

    monkeypatch.setattr(hp.sqlite3, "connect", fail)
    with pytest.raises(hp.sqlite3.OperationalError):
        run(tmp_path, [], max_requests=1)
    assert not (tmp_path / "healthplanet" / "healthplanet.sqlite3").exists()
    monkeypatch.setattr(hp.sqlite3, "connect", connect)
    result, _ = run(tmp_path, [Response(payload())], max_requests=1)
    assert result["requests_made"] == 1


def test_partial_rescan_resumes_all_unfinished_targets_despite_old_success(tmp_path):
    run(tmp_path, [Response(payload()) for _ in range(3)])
    result, _ = run(tmp_path, [Response(b"failed", 500)], max_requests=1, rescan=True)
    assert result["remaining_windows"] == 3
    assert hp.export_data(tmp_path)["status"] == "partial"
    result, session = run(tmp_path, [Response(payload()) for _ in range(3)])
    assert len(session.calls) == 3
    assert result["remaining_windows"] == 0
    assert hp.export_data(tmp_path)["status"] == "available"


def test_failed_archive_write_cannot_complete_window(tmp_path, monkeypatch):
    def fail(self, body):
        raise OSError("disk full")

    monkeypatch.setattr(hp.Archive, "put", fail)
    with pytest.raises(OSError):
        run(tmp_path, [Response(payload(measure()))], max_requests=1)
    assert hp.export_data(tmp_path)["sources"][0]["intervals"] == []


def test_web_export_uses_latest_healthplanet_body_measurements_and_keeps_all_points(tmp_path):
    from health.store import Store
    from health.web_export import export_web

    run(
        tmp_path,
        [
            Response(
                payload(
                    measure(),
                    measure("202609072000", value="61"),
                    measure("202609072000", tag="6022", value="28.5"),
                )
            )
        ],
        max_requests=1,
    )
    store = Store(tmp_path / "health.duckdb")
    try:
        store.upsert_daily([("weight_kg", "2026-09-07", 99), ("fat_pct", "2026-09-07", 44)])
        manifest = export_web(store, tmp_path / "web")
        meta = json.loads(manifest.read_text())
        base = manifest.parent / meta["basePath"]
        data = json.loads((base / "healthplanet.json").read_text())["data"]
        assert len(data["measurements"]) == 3
        daily = json.loads((base / "daily.json").read_text())["data"]
        assert daily["series"]["weight_kg"] == [61]
        assert daily["series"]["fat_pct"] == [28.5]
        assert daily["providers"]["weight_kg"] == "healthplanet"
        assert daily["providers"]["fat_pct"] == "healthplanet"
        assert data["provider"] == "healthplanet"
        assert "SYNTHETIC_SECRET" not in json.dumps(data)
    finally:
        store.close()


def test_web_export_includes_healthplanet_body_series_without_google_body_rows(tmp_path):
    from health.store import Store
    from health.web_export import export_web

    run(
        tmp_path,
        [Response(payload(measure(), measure(tag="6022", value="28.5")))],
        max_requests=1,
    )
    store = Store(tmp_path / "health.duckdb")
    try:
        store.upsert_daily([("steps", "2026-09-07", 1234)])
        manifest = export_web(store, tmp_path / "web")
        meta = json.loads(manifest.read_text())
        daily = json.loads((manifest.parent / meta["basePath"] / "daily.json").read_text())["data"]
        assert daily["series"]["weight_kg"] == [60.25]
        assert daily["series"]["fat_pct"] == [28.5]
        assert daily["providers"]["weight_kg"] == "healthplanet"
        assert daily["providers"]["fat_pct"] == "healthplanet"
    finally:
        store.close()


def test_cli_healthplanet_sync_is_independent_of_google(tmp_path, monkeypatch, capsys):
    from health import cli

    selected = []

    def fake_healthplanet(args):
        selected.extend(args.endpoint)
        return 0, {"command": args.command, "status": "available"}

    monkeypatch.setattr(cli, "_healthplanet", fake_healthplanet)
    assert (
        cli.main(
            [
                "--data-dir",
                str(tmp_path),
                "sync-healthplanet",
                "--history-start",
                "2020-01-01",
                "--endpoint",
                "innerscan",
            ]
        )
        == 0
    )
    assert selected == ["innerscan"]
    assert json.loads(capsys.readouterr().out)["command"] == "sync-healthplanet"


def test_wait_mode_resumes_quota_then_stops_when_requested_range_finishes(tmp_path, monkeypatch):
    from health.healthplanet_auth import HealthPlanetAuth

    from health import cli

    monkeypatch.setattr(HealthPlanetAuth, "from_env", lambda *args: Auth())
    responses = iter(
        [
            {
                "status": "partial",
                "stopped_reason": "request_cap",
                "retry_after_s": None,
                "failures": [],
                "requests_made": 3,
            },
            {
                "status": "partial",
                "stopped_reason": "rate_limited",
                "retry_after_s": 20,
                "failures": [],
                "requests_made": 0,
            },
            {
                "status": "available",
                "stopped_reason": None,
                "retry_after_s": None,
                "failures": [],
                "requests_made": 2,
            },
        ]
    )
    calls, waits = [], []

    def fake_sync(*args, **kwargs):
        calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(hp, "sync", fake_sync)
    monkeypatch.setattr(cli.time, "sleep", waits.append)
    assert (
        cli.main(
            [
                "--data-dir",
                str(tmp_path),
                "sync-healthplanet",
                "--history-start",
                "2010-01-01",
                "--endpoint",
                "innerscan",
                "--wait",
            ]
        )
        == 0
    )
    assert len(calls) == 3
    assert all(call["endpoints"] == ["innerscan"] for call in calls)
    assert waits == [21]


def test_wait_mode_does_not_retry_endpoint_failures(tmp_path, monkeypatch):
    from health.healthplanet_auth import HealthPlanetAuth

    from health import cli

    monkeypatch.setattr(HealthPlanetAuth, "from_env", lambda *args: Auth())

    def failed(*args, **kwargs):
        return {
            "status": "partial",
            "stopped_reason": "request_cap",
            "retry_after_s": None,
            "requests_made": 1,
            "failures": [{"status": "permission_denied"}],
        }

    monkeypatch.setattr(hp, "sync", failed)

    def no_sleep(seconds):
        pytest.fail("must not wait after an endpoint failure")

    monkeypatch.setattr(cli.time, "sleep", no_sleep)
    assert (
        cli.main(
            [
                "--data-dir",
                str(tmp_path),
                "sync-healthplanet",
                "--history-start",
                "2010-01-01",
                "--wait",
            ]
        )
        == 2
    )
