"""Offline CLI integration: one writer, durable backups and bounded HTTP."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest
from health.archive_index import ArchiveIndex
from health.archive_sync import ArchiveReport
from health.auth import SCOPES, AuthError
from health.client import HealthClient
from health.endpoints import CATALOG
from health.source_catalog import load_sources
from health.store import Store
from health.sync import SyncReport

from health import cli

from .fakes import FakeResponse, FakeSession


class FakeAuth:
    def load_tokens(self):
        return {"scope": SCOPES, "access_token": "SYNTHETIC_TOKEN"}

    def access_token(self):
        return "SYNTHETIC_TOKEN"

    def refresh(self):
        return {}


@pytest.fixture
def offline(monkeypatch, tmp_path):
    source = next(
        s for s in load_sources() if s.data_type == "steps" and s.preferred_method == "list"
    )
    source = replace(source, unbounded_verified=True)
    monkeypatch.setattr(cli, "load_sources", lambda: (source,))
    monkeypatch.setattr(cli, "CATALOG", [next(m for m in CATALOG if m.name == "steps")])
    calls = []
    auth = FakeAuth()

    def from_env(data_dir, env_path=None, *, scopes=None):
        calls.append((data_dir, env_path, scopes))
        return auth

    monkeypatch.setattr(cli.GoogleHealthAuth, "from_env", from_env)

    class FixedDate(date):
        @classmethod
        def today(cls):
            return date(2026, 7, 2)

    monkeypatch.setattr(cli, "date", FixedDate)
    return SimpleNamespace(source=source, auth=auth, calls=calls, data=tmp_path / "data")


def command(offline, *args):
    return cli.main(["--data-dir", str(offline.data), *args])


def output(capsys):
    captured = capsys.readouterr()
    assert "SYNTHETIC_TOKEN" not in captured.out + captured.err
    assert "SECRET_RAW" not in captured.out + captured.err
    return json.loads(captured.out), captured.err


def install_transport(monkeypatch, responses):
    session = FakeSession(responses)
    clients = []

    def client(auth):
        value = HealthClient(auth, session=session, min_interval_s=0)
        clients.append(value)
        return value

    monkeypatch.setattr(cli, "HealthClient", client)
    return session, clients


def test_auth_uses_explicit_paths_scopes_and_no_browser_without_database(
    offline, monkeypatch, capsys
):
    observed = []
    monkeypatch.setattr(
        cli, "authorize", lambda auth, *, open_browser: observed.append(open_browser)
    )
    env = offline.data.parent / "synthetic.env"
    result = cli.main(
        ["--data-dir", str(offline.data), "--env-file", str(env), "auth", "--no-browser"]
    )
    assert result == 0
    assert observed == [False]
    assert offline.calls == [(offline.data, env, " ".join(offline.source.readonly_scopes))]
    assert not (offline.data / "health.duckdb").exists()
    summary, _ = output(capsys)
    assert summary["status"] == "complete"


@pytest.mark.parametrize(
    "args",
    [
        ["sync", "--max-requests", "0"],
        ["sync", "--max-requests", "-1"],
        ["sync", "--max-requests", "SECRET_RAW"],
        ["--SECRET_RAW"],
        ["sync", "--history-start", "SECRET_RAW"],
        ["sync", "--history-start", "9999-01-01"],
    ],
)
def test_invalid_arguments_do_not_echo_untrusted_values(offline, capsys, args):
    assert command(offline, *args) == 1
    summary, _ = output(capsys)
    assert summary["stopped_reason"] == "configuration"
    assert not offline.data.exists()


def test_export_backups_legacy_database_before_store_ddl_without_auth(
    tmp_path, monkeypatch, capsys
):
    data = tmp_path / "data"
    data.mkdir()
    db = data / "health.duckdb"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE legacy_only (value INTEGER)")
    con.execute("INSERT INTO legacy_only VALUES (42)")
    con.close()
    opened = []

    def open_store(path):
        backups = list((data / "backups").glob("*.duckdb"))
        assert len(backups) == 1
        backup = duckdb.connect(str(backups[0]), read_only=True)
        assert backup.execute("SHOW TABLES").fetchall() == [("legacy_only",)]
        assert backup.execute("SELECT * FROM legacy_only").fetchone() == (42,)
        backup.close()
        opened.append(path)
        return Store(path)

    monkeypatch.setattr(cli, "Store", open_store)

    def no_auth(*args, **kwargs):
        pytest.fail("export must not resolve auth or call a live API")

    monkeypatch.setattr(cli.GoogleHealthAuth, "from_env", no_auth)
    assert (
        cli.main(["--data-dir", str(data), "export-web", "--out-dir", str(tmp_path / "web")]) == 0
    )
    assert opened == [db]
    assert (tmp_path / "web" / "meta.json").exists()
    summary, _ = output(capsys)
    assert summary["command"] == "export-web" and summary["backup_created"] is True
    assert str(tmp_path) not in json.dumps(summary)


def test_backup_failure_never_opens_store(offline, monkeypatch, capsys):
    def fail(*args):
        raise OSError("SECRET_RAW /private/token.json")

    monkeypatch.setattr(cli, "backup_database", fail)
    monkeypatch.setattr(cli, "Store", lambda *args: pytest.fail("Store opened after failed backup"))
    assert command(offline, "export-web", "--out-dir", str(offline.data.parent / "web")) == 1
    summary, _ = output(capsys)
    assert summary["stopped_reason"] == "storage_error"


def fake_engines(monkeypatch):
    visits = []

    class Archive:
        def __init__(self, client, archive, index, sources, **kwargs):
            self.client = client
            self.index = index
            for source in sources:
                index.register(source)

        def sync(self, budget, *, rescan=False):
            assert self.client.response_observer is None
            for _ in range(budget.limit):
                budget.consume()
            visits.append(("archive", budget.limit, rescan))
            return ArchiveReport(
                requests_made=budget.used, remaining=1, stopped_reason="request_cap"
            )

    class Projection:
        def __init__(self, client, store, *, budget, **kwargs):
            self.client, self.budget = client, budget

        def sync_all(self, progress_cb=None):
            assert self.client.response_observer is not None
            for _ in range(self.budget.limit):
                self.budget.consume()
            visits.append(("projection", self.budget.limit, False))
            return SyncReport(requests_made=self.budget.used, stopped_early=True)

    monkeypatch.setattr(cli, "ArchiveEngine", Archive)
    monkeypatch.setattr(cli, "SyncEngine", Projection)
    return visits


def test_cap_one_alternates_persistently_without_starving_either_side(offline, monkeypatch, capsys):
    visits = fake_engines(monkeypatch)
    _, clients = install_transport(monkeypatch, [])
    assert command(offline, "sync", "--max-requests", "1") == 2
    first, _ = output(capsys)
    assert command(offline, "sync", "--max-requests", "1") == 2
    second, _ = output(capsys)
    assert visits == [("archive", 1, False), ("projection", 1, False)]
    assert first["requests_made"] == second["requests_made"] == 1
    # The fake projection reports no remaining chunks but writes no checkpoint.
    assert second["projection_remaining"] == 1
    assert (first["run_number"], second["run_number"]) == (1, 2)
    assert all(client.response_observer is None for client in clients)


@pytest.mark.parametrize("check", ["requests_and_checkpoints", "pending_unvisited"])
def test_real_cli_cap_one_rotates_projection_across_eight_reopens(
    offline, monkeypatch, capsys, check
):
    metrics = [next(m for m in CATALOG if m.name == name) for name in ("steps", "distance")]
    monkeypatch.setattr(cli, "CATALOG", metrics)
    session, _ = install_transport(
        monkeypatch,
        [FakeResponse(json_data={"dataPoints": []})]
        + [FakeResponse(json_data={"rollupDataPoints": []}) for _ in range(7)],
    )
    snapshots = []
    projection_phases = 0
    for _ in range(8):
        before = len(session.calls)
        assert command(offline, "sync", "--max-requests", "1", "--history-start", "2026-06-26") == 2
        summary, _ = output(capsys)
        assert len(session.calls) - before == summary["requests_made"] == 1
        projection_phases += int(summary["budgets"]["projection"]["limit"] > 0)
        with duckdb.connect(str(offline.data / "health.duckdb"), read_only=True) as con:
            checkpoints = dict(
                con.execute("SELECT metric, backfilled_from FROM sync_state").fetchall()
            )
            cursor = con.execute(
                "SELECT value FROM archive_meta WHERE key = 'projection_cursor'"
            ).fetchone()
        assert cursor == ((str(projection_phases),) if projection_phases else None)
        snapshots.append((summary, checkpoints))

    if check == "requests_and_checkpoints":
        for metric in metrics:
            assert any(
                call["method"] == "POST"
                and f"/dataTypes/{metric.data_type}/dataPoints:dailyRollUp" in call["url"]
                for call in session.calls
            ), f"{metric.name} never received a projection request"
            assert snapshots[-1][1][metric.name] == date(2026, 6, 26)
    else:
        unvisited = [summary for summary, checkpoints in snapshots if len(checkpoints) < 2]
        assert unvisited
        assert all(summary["projection_remaining"] > 0 for summary in unvisited)


def test_odd_cap_and_rescan_are_shared_without_extra_requests(offline, monkeypatch, capsys):
    visits = fake_engines(monkeypatch)
    install_transport(monkeypatch, [])
    assert command(offline, "sync", "--max-requests", "5", "--rescan") == 2
    summary, _ = output(capsys)
    assert visits == [("archive", 3, True), ("projection", 2, False)]
    assert summary["requests_made"] == 5
    assert sum(row["used"] for row in summary["budgets"].values()) == 5


def test_archive_only_gives_the_full_request_budget_to_original_sources(
    offline, monkeypatch, capsys
):
    visits = fake_engines(monkeypatch)
    install_transport(monkeypatch, [])

    assert command(offline, "sync", "--max-requests", "5", "--archive-only") == 2

    summary, _ = output(capsys)
    assert visits == [("archive", 5, False)]
    assert summary["budgets"] == {
        "archive": {"limit": 5, "used": 5},
        "projection": {"limit": 0, "used": 0},
    }
    assert summary["requests_made"] == 5


def test_rate_limit_stops_both_engines_without_leaking_api_body(offline, monkeypatch, capsys):
    session, clients = install_transport(
        monkeypatch,
        [FakeResponse(429, {"error": {"message": "SECRET_RAW"}}, headers={"Retry-After": "17"})],
    )
    assert command(offline, "sync", "--max-requests", "4") == 1
    summary, _ = output(capsys)
    assert summary["stopped_reason"] == "rate_limited"
    assert summary["retry_after_s"] == 17
    assert summary["requests_made"] == len(session.calls) == 1
    assert clients[0].response_observer is None


def test_parser_failure_preserves_projection_raw_and_previous_typed_rows(
    offline, monkeypatch, capsys
):
    store = Store(offline.data / "health.duckdb")
    store.upsert_daily([("steps", "2026-07-02", 999)])
    store.set_sync_state("steps", date(2026, 7, 2))
    index = ArchiveIndex(store.con)
    index.next_run()  # Next CLI run starts with projection.
    store.close()
    body = b'{"rollupDataPoints":"SECRET_RAW"}'
    session, clients = install_transport(
        monkeypatch, [FakeResponse(content=body), FakeResponse(json_data={"dataPoints": []})]
    )
    assert command(offline, "sync", "--max-requests", "2") == 2
    summary, _ = output(capsys)
    assert summary["requests_made"] == len(session.calls) == 2
    assert clients[0].response_observer is None
    store = Store(offline.data / "health.duckdb")
    try:
        assert store.daily_frame(["steps"])["steps"].tolist() == [999]
        assert store.get_sync_state("steps") == date(2026, 7, 2)
        rows = ArchiveIndex(store.con, initialize=False).coverage()
        projected = next(row for row in rows if row["stream_id"] == "projection:steps")
        assert projected["status"] == "failed" and projected["pages"] == 1
        assert projected["history_complete"] is False
        source = next(row for row in rows if row["stream_id"] == offline.source.key)
        assert source["pages"] == 1
        import gzip

        bodies = [
            gzip.decompress(path.read_bytes())
            for path in (offline.data / "archive" / "objects").glob("*.json.gz")
        ]
        assert body in bodies
    finally:
        store.close()


def test_successful_projection_and_source_are_separate_complete_queries(
    offline, monkeypatch, capsys
):
    payload = json.loads((Path(__file__).parent / "fixtures" / "rollup_steps.json").read_text())
    session, _ = install_transport(
        monkeypatch,
        [
            FakeResponse(json_data={"dataPoints": []}),
            FakeResponse(json_data=payload),
            FakeResponse(json_data=payload),
        ],
    )
    assert command(offline, "sync", "--max-requests", "3", "--history-start", "2026-06-26") == 0
    summary, _ = output(capsys)
    assert summary["requests_made"] == len(session.calls) <= 3
    store = Store(offline.data / "health.duckdb")
    try:
        assert store.daily_frame(["steps"])["steps"].tolist() == [8000, 9000]
        row = next(
            row
            for row in ArchiveIndex(store.con, initialize=False).coverage()
            if row["stream_id"] == "projection:steps"
        )
        assert row["status"] == "complete" and row["points"] == 2
        assert row["history_complete"] is False
    finally:
        store.close()


def test_history_floors_use_confirmed_intervals_or_explicit_bound():
    catalog = [next(m for m in CATALOG if m.name == "steps")]
    coverage = [
        {
            "stream_id": "steps:list",
            "data_type": "steps",
            "representation": "source",
            "intervals": [{"start": "2018-01-01", "end": "2018-02-01", "status": "complete"}],
        }
    ]
    assert cli.projection_history_floors(coverage, catalog, today=date(2026, 7, 2)) == {
        "steps": date(2018, 1, 1)
    }
    assert cli.projection_history_floors(
        coverage, catalog, today=date(2026, 7, 2), history_start=date(2020, 1, 1)
    ) == {"steps": date(2020, 1, 1)}
    coverage[0]["representation"] = "legacy_json"
    assert cli.projection_history_floors(coverage, catalog, today=date(2026, 7, 2)) == {
        "steps": date(2026, 6, 26)
    }


def test_auth_failure_is_safe_and_does_not_migrate(offline, monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise AuthError("SECRET_RAW client_secret=SYNTHETIC_TOKEN")

    monkeypatch.setattr(cli.GoogleHealthAuth, "from_env", fail)
    assert command(offline, "sync") == 1
    summary, _ = output(capsys)
    assert summary["stopped_reason"] == "authorization"
    assert not offline.data.exists()


def test_exit_status_distinguishes_incomplete_from_stopped():
    assert cli.exit_status(stopped=False, incomplete=False) == 0
    assert cli.exit_status(stopped=False, incomplete=True) == 2
    assert cli.exit_status(stopped=True, incomplete=True) == 1


def save_profile(data_dir, membership_date):
    from health.archive import Archive

    store = Store(data_dir / "health.duckdb")
    index = ArchiveIndex(store.con)
    source = next(s for s in load_sources() if s.data_type == "profile")
    index.register(source)
    attempt = index.start(source.key, {}, "metadata")
    reference = Archive(data_dir / "archive").put(
        json.dumps(
            {"membershipStartDate": membership_date, "name": "users/SYNTHETIC_TOKEN/profile"}
        ).encode()
    )
    index.record_page(attempt, 0, reference, 200, 1)
    index.confirm_terminal(attempt, next_page_token=None)
    index.finish(attempt, "complete", history_complete=True)
    store.close()


def test_saved_official_account_first_date_is_passed_to_both_engines(offline, monkeypatch, capsys):
    save_profile(offline.data, {"year": 2014, "month": 3, "day": 7})
    fake_engines(monkeypatch)
    original_archive = cli.ArchiveEngine
    original_projection = cli.SyncEngine
    observed = []

    class Archive(original_archive):
        def __init__(self, *args, **kwargs):
            observed.append(kwargs["history_start"])
            super().__init__(*args, **kwargs)

    class Projection(original_projection):
        def __init__(self, *args, **kwargs):
            observed.append(kwargs["history_floors"]["steps"])
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(cli, "ArchiveEngine", Archive)
    monkeypatch.setattr(cli, "SyncEngine", Projection)
    install_transport(monkeypatch, [])
    assert command(offline, "sync", "--max-requests", "2") == 2
    summary, _ = output(capsys)
    assert observed == [date(2014, 3, 7), date(2014, 3, 7)]
    assert summary["projection_history"]["steps"] == {
        "start": "2014-03-07",
        "basis": "account_profile",
    }


def test_missing_history_boundary_is_disclosed_even_after_successful_recent_projection(
    offline, monkeypatch, capsys
):
    payload = {"rollupDataPoints": []}
    install_transport(
        monkeypatch,
        [
            FakeResponse(json_data={"dataPoints": []}),
            FakeResponse(json_data=payload),
            FakeResponse(json_data=payload),
        ],
    )
    assert command(offline, "sync", "--max-requests", "3") == 2
    summary, _ = output(capsys)
    assert summary["projection_history"]["steps"]["basis"] == "unknown_history"
    assert summary["projection_history"]["steps"]["start"] == "2026-06-26"


def test_invalid_account_date_never_becomes_a_history_boundary(offline):
    from health.archive import Archive

    save_profile(offline.data, {"year": 2014, "month": 0, "day": 0})
    store = Store(offline.data / "health.duckdb")
    try:
        assert (
            cli.account_first_date(
                ArchiveIndex(store.con, initialize=False),
                Archive(offline.data / "archive"),
                today=date(2026, 7, 2),
            )
            is None
        )
    finally:
        store.close()


def test_unused_archive_share_is_borrowed_by_projection(offline, monkeypatch, capsys):
    visits = fake_engines(monkeypatch)

    class Archive(cli.ArchiveEngine):
        def sync(self, budget, *, rescan=False):
            budget.consume()
            return ArchiveReport(requests_made=1)

    monkeypatch.setattr(cli, "ArchiveEngine", Archive)
    install_transport(monkeypatch, [])
    assert command(offline, "sync", "--max-requests", "5") == 2
    summary, _ = output(capsys)
    assert visits == [("projection", 4, False)]
    assert summary["budgets"] == {
        "archive": {"limit": 3, "used": 1},
        "projection": {"limit": 4, "used": 4},
    }
    assert summary["requests_made"] == 5


def test_missing_grant_is_explicit_and_sends_nothing(offline, monkeypatch, capsys):
    monkeypatch.setattr(
        offline.auth, "load_tokens", lambda: {"scope": "", "access_token": "SYNTHETIC_TOKEN"}
    )
    session, _ = install_transport(monkeypatch, [])
    assert command(offline, "sync", "--max-requests", "4") == 2
    summary, _ = output(capsys)
    assert session.calls == []
    assert summary["missing_scopes"] == list(offline.source.readonly_scopes)
    assert any(
        failure["stream_id"] == "projection:steps" and failure["status"] == "permission_denied"
        for failure in summary["failures"]
    )


def test_401_retry_and_parser_failure_cannot_exceed_total_cap(offline, monkeypatch, capsys):
    session, _ = install_transport(
        monkeypatch,
        [
            FakeResponse(401, {"error": {"message": "SECRET_RAW"}}),
            FakeResponse(json_data={"rollupDataPoints": []}),
        ],
    )
    assert command(offline, "sync", "--max-requests", "2") == 2
    summary, _ = output(capsys)
    assert summary["requests_made"] == len(session.calls) == 2
    assert summary["budgets"]["archive"]["used"] == 1
    assert summary["budgets"]["projection"]["used"] == 1


def test_projection_second_page_failure_preserves_both_pages_and_no_terminal_gate(
    offline, monkeypatch, capsys
):
    from health.archive import Archive
    from health.client import RequestBudget
    from health.sync import SyncEngine

    metric = next(m for m in CATALOG if m.name == "intraday_hr")
    store = Store(offline.data / "health.duckdb")
    store.upsert_intraday([("hr", "2026-07-02T00:00:00", 99)])
    index = ArchiveIndex(store.con)
    archive = Archive(offline.data / "archive")
    capture = cli._ProjectionCapture(archive, index, [metric])
    client = HealthClient(
        offline.auth,
        session=FakeSession(
            [
                FakeResponse(json_data={"dataPoints": [], "nextPageToken": "SYNTHETIC_TOKEN"}),
                FakeResponse(403, {"error": {"message": "SECRET_RAW"}}),
            ]
        ),
        min_interval_s=0,
        response_observer=capture,
    )
    try:
        report = SyncEngine(
            client,
            store,
            catalog=[metric],
            today=date(2026, 7, 2),
            history_floors={metric.name: date(2026, 7, 2)},
            budget=RequestBudget(2),
        ).sync_all(progress_cb=capture.committed)
        capture.failures(report.failures)
        row = index.coverage()[0]
        assert row["pages"] == 2 and row["status"] == "permission_denied"
        assert store.con.execute("SELECT count(*) FROM archive_terminal").fetchone() == (0,)
        assert store.intraday_frame("hr", date(2026, 7, 2))["value"].tolist() == [99]
    finally:
        store.close()


@pytest.mark.parametrize("name", ["steps", "intraday_hr"])
def test_omitted_repeated_field_is_a_valid_empty_projection(name, offline):
    from health.archive import Archive
    from health.client import RequestBudget
    from health.sync import SyncEngine

    metric = next(m for m in CATALOG if m.name == name)
    store = Store(offline.data / "health.duckdb")
    index = ArchiveIndex(store.con)
    capture = cli._ProjectionCapture(Archive(offline.data / "archive"), index, [metric])
    client = HealthClient(
        offline.auth,
        session=FakeSession([FakeResponse(json_data={}), FakeResponse(json_data={})]),
        min_interval_s=0,
        response_observer=capture,
    )
    try:
        report = SyncEngine(
            client,
            store,
            catalog=[metric],
            today=date(2026, 7, 2),
            history_floors={name: date(2026, 7, 2)},
            budget=RequestBudget(2),
        ).sync_all(progress_cb=capture.committed)
        assert report.failures == []
        assert index.coverage()[0]["status"] == "empty"
        assert index.coverage()[0]["points"] == 0
    finally:
        store.close()


def test_existing_local_history_is_never_replaced_by_recent_default(offline, monkeypatch, capsys):
    store = Store(offline.data / "health.duckdb")
    store.upsert_daily([("steps", "2016-05-04", 10)])
    store.close()
    fake_engines(monkeypatch)
    install_transport(monkeypatch, [])
    assert command(offline, "sync", "--max-requests", "2") == 2
    summary, _ = output(capsys)
    assert summary["projection_history"]["steps"] == {
        "start": "2016-05-04",
        "basis": "local_history",
    }


def test_unbounded_raw_observation_extends_projection_without_proving_full_history(
    offline, monkeypatch, capsys
):
    from health.archive import Archive

    store = Store(offline.data / "health.duckdb")
    index = ArchiveIndex(store.con)
    index.register(offline.source)
    attempt = index.start(offline.source.key, {"params": {}}, "source")
    body = {
        "dataPoints": [
            {
                "steps": {
                    "interval": {"civilStartTime": {"date": {"year": 2012, "month": 4, "day": 3}}}
                }
            }
        ]
    }
    reference = Archive(offline.data / "archive").put(json.dumps(body).encode())
    index.record_page(attempt, 0, reference, 200, 1)
    index.finish(attempt, "unknown_history", "unbounded semantics not verified")
    store.close()
    fake_engines(monkeypatch)
    install_transport(monkeypatch, [])
    assert command(offline, "sync", "--max-requests", "2") == 2
    summary, _ = output(capsys)
    assert summary["projection_history"]["steps"] == {
        "start": "2012-04-03",
        "basis": "source_observed",
    }
    assert summary["remaining"] > 0
    assert any(row["status"] == "unknown_history" for row in summary["failures"])
