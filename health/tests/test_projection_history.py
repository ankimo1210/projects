from dataclasses import replace
from datetime import date, datetime

from health.client import RequestBudget
from health.endpoints import CATALOG, ParsedRows
from health.store import Store
from health.sync import SyncEngine


def test_extended_intraday_history_never_deletes_daily_series(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    day = date(2020, 1, 1)
    store.upsert_daily([("steps", day, 123.0)])
    store.upsert_intraday([("steps", datetime(2020, 1, 1, 1), 5.0)])
    intraday = replace(next(m for m in CATALOG if m.name == "intraday_steps"), full_history=True)
    store.replace_chunk(intraday, day, day, [{"dataPoints": []}], ParsedRows())
    assert store.daily_frame(["steps"]).iloc[0]["steps"] == 123.0
    assert store.intraday_frame("steps", day).empty
    store.close()


def test_confirmed_floor_can_extend_intraday_beyond_thirty_days(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    metric = next(m for m in CATALOG if m.name == "intraday_hr")
    engine = SyncEngine(
        None,
        store,
        [metric],
        today=date(2026, 9, 7),
        history_floors={metric.name: date(2010, 1, 1)},
    )
    assert engine._floor(metric) == date(2010, 1, 1)
    store.close()


def test_shared_budget_counts_only_this_projection_run(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    budget = RequestBudget(2)
    budget.consume()

    class Client:
        def daily_rollup(self, metric, start, end, budget):
            budget.consume()
            return {}

    metric = replace(CATALOG[0], parse_pages=lambda pages: ParsedRows())
    engine = SyncEngine(
        Client(),
        store,
        [metric],
        today=date(2026, 9, 7),
        environ={"HEALTH_BACKFILL_START": "2026-09-07"},
        budget=budget,
    )
    report = engine.sync_all()
    assert report.requests_made == 1
    assert budget.used == 2
    store.close()


# A 30-day aligned chunk straddles 2020-02-01: 2020-01-16..2020-02-14.
# Recording its key instead of the clipped request start loses Jan 16..31
# when a later explicit policy expands the floor to Jan 1.
class HistoryClient:
    def __init__(self, fail_range=None):
        self.calls = []
        self.fail_range = fail_range

    def daily_rollup(self, metric, start, end, budget):
        from health.client import ApiError

        budget.consume()
        self.calls.append((start, end))
        if self.fail_range == (start, end):
            raise ApiError(403, "synthetic denied boundary")
        return {"days": [day.isoformat() for day in _days(start, end)]}


def _days(start, end):
    from datetime import timedelta

    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _history_metric():
    return replace(
        next(m for m in CATALOG if m.name == "steps"),
        max_range_days=30,
        parse_pages=lambda pages: ParsedRows(
            daily=tuple(
                ("steps", date.fromisoformat(day), 1.0) for page in pages for day in page["days"]
            )
        ),
    )


def _sync_history(store, client, floor, *, max_requests=100, metric=None):
    return SyncEngine(
        client,
        store,
        [metric or _history_metric()],
        today=date(2020, 4, 30),
        history_floors={"steps": floor},
        environ={},
        max_requests=max_requests,
    ).sync_all()


def _seed_legacy_boundary(store):
    from health.endpoints import aligned_chunk

    _sync_history(store, HistoryClient(), date(2020, 2, 1))
    # Emulate the old implementation even after the new request-start fix.
    boundary, _ = aligned_chunk(date(2020, 2, 1), 30)
    store.con.execute(
        "UPDATE sync_state SET backfilled_from = ? WHERE metric = 'steps'", [boundary]
    )


def test_expanding_explicit_floor_requests_every_missing_january_day(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    try:
        _sync_history(store, HistoryClient(), date(2020, 2, 1))
        client = HistoryClient()
        report = _sync_history(store, client, date(2020, 1, 1))
        requested = {day for start, end in client.calls for day in _days(start, end)}
        assert set(_days(date(2020, 1, 1), date(2020, 1, 31))) <= requested
        saved = {
            row[0]
            for row in store.con.execute(
                "SELECT date FROM daily_series WHERE metric='steps'"
            ).fetchall()
        }
        assert set(_days(date(2020, 1, 1), date(2020, 2, 29))) <= saved
        assert report.history_remaining == {"steps": 0}
    finally:
        store.close()


def test_new_checkpoint_records_actual_clipped_start(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    try:
        _sync_history(store, HistoryClient(), date(2020, 2, 1))
        assert store.get_sync_checkpoint("steps").backfilled_from == date(2020, 2, 1)
    finally:
        store.close()


def test_legacy_boundary_repaired_once_per_floor_across_reopens(tmp_path):
    path = tmp_path / "health.duckdb"
    store = Store(path)
    _seed_legacy_boundary(store)
    # Unrelated series and rows outside the requested history must survive.
    store.upsert_daily([("steps", date(2019, 1, 1), 7.0), ("other", date(2020, 1, 20), 9.0)])
    store.upsert_intraday([("steps", datetime(2020, 1, 20, 1), 42.0)])
    client = HistoryClient()
    _sync_history(store, client, date(2020, 1, 1))
    assert client.calls.count((date(2020, 1, 16), date(2020, 2, 14))) == 1
    assert (
        store.con.execute(
            "SELECT count(*) FROM sync_history_policy WHERE metric='steps' AND floor=DATE '2020-01-01'"
        ).fetchone()[0]
        == 1
    )
    assert store.con.execute(
        "SELECT value FROM daily_series WHERE metric='steps' AND date=DATE '2019-01-01'"
    ).fetchone() == (7.0,)
    assert store.con.execute("SELECT value FROM daily_series WHERE metric='other'").fetchone() == (
        9.0,
    )
    assert store.con.execute("SELECT value FROM intraday WHERE metric='steps'").fetchone() == (
        42.0,
    )
    store.close()
    store = Store(path)
    try:
        repeated = HistoryClient()
        _sync_history(store, repeated, date(2020, 1, 1))
        assert repeated.calls == [(date(2020, 4, 15), date(2020, 4, 30))]
        expanded = HistoryClient()
        _sync_history(store, expanded, date(2019, 12, 1))
        assert expanded.calls.count((date(2019, 12, 17), date(2020, 1, 15))) == 1
        assert (
            store.con.execute(
                "SELECT count(*) FROM sync_history_policy WHERE metric='steps' AND floor=DATE '2019-12-01'"
            ).fetchone()[0]
            == 1
        )
    finally:
        store.close()


def test_failed_repair_is_not_marked_and_retries_after_restart(tmp_path):
    path = tmp_path / "health.duckdb"
    store = Store(path)
    _seed_legacy_boundary(store)
    boundary = (date(2020, 1, 16), date(2020, 2, 14))
    report = _sync_history(store, HistoryClient(fail_range=boundary), date(2020, 1, 1))
    assert report.failures
    assert (
        store.con.execute(
            "SELECT count(*) FROM sync_history_policy WHERE floor=DATE '2020-01-01'"
        ).fetchone()[0]
        == 0
    )
    assert store.get_sync_checkpoint("steps").backfilled_from == date(2020, 1, 16)
    store.close()
    store = Store(path)
    try:
        client = HistoryClient()
        _sync_history(store, client, date(2020, 1, 1))
        assert boundary in client.calls
    finally:
        store.close()


def test_capped_repair_remains_pending_until_success(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    try:
        _seed_legacy_boundary(store)
        first = _sync_history(store, HistoryClient(), date(2020, 1, 1), max_requests=1)
        assert first.stopped_early
        assert first.history_remaining == {"steps": 2}  # repair plus older chunk
        assert (
            store.con.execute(
                "SELECT count(*) FROM sync_history_policy WHERE floor=DATE '2020-01-01'"
            ).fetchone()[0]
            == 0
        )
        second = _sync_history(store, HistoryClient(), date(2020, 1, 1), max_requests=2)
        assert second.history_remaining == {"steps": 1}
        assert (
            store.con.execute(
                "SELECT count(*) FROM sync_history_policy WHERE floor=DATE '2020-01-01'"
            ).fetchone()[0]
            == 1
        )
        _sync_history(store, HistoryClient(), date(2020, 1, 1))
        assert store.get_sync_checkpoint("steps").backfilled_from == date(2020, 1, 1)
    finally:
        store.close()


def test_parser_failure_does_not_acknowledge_legacy_repair(tmp_path):
    from health.endpoints import PayloadError

    store = Store(tmp_path / "health.duckdb")
    try:
        _seed_legacy_boundary(store)
        metric = _history_metric()

        def parse(pages):
            if pages[0]["days"][0] == "2020-01-16":
                raise PayloadError(metric.name, "synthetic invalid boundary")
            return metric.parse_pages(pages)

        report = _sync_history(
            store,
            HistoryClient(),
            date(2020, 1, 1),
            metric=replace(metric, parse_pages=parse),
        )
        assert report.failures[0].kind == "payload"
        assert not store.history_boundary_repaired("steps", date(2020, 1, 1))
        assert store.get_sync_checkpoint("steps").backfilled_from == date(2020, 1, 16)
    finally:
        store.close()


def test_policy_write_failure_rolls_back_replacement_and_checkpoint(tmp_path, monkeypatch):
    import duckdb
    import pytest

    store = Store(tmp_path / "health.duckdb")
    try:
        _seed_legacy_boundary(store)
        old = store.get_sync_checkpoint("steps")
        raw = store.con.execute(
            "SELECT payload FROM raw_json WHERE metric='steps' AND range_start=DATE '2020-01-16'"
        ).fetchall()
        daily = store.con.execute("SELECT * FROM daily_series ORDER BY metric, date").fetchall()
        connection = store.con

        class FailingPolicyConnection:
            def execute(self, sql, *args):
                if "INSERT INTO sync_history_policy" in sql:
                    raise duckdb.Error("synthetic policy write failure")
                return connection.execute(sql, *args)

            def __getattr__(self, name):
                return getattr(connection, name)

        monkeypatch.setattr(store, "con", FailingPolicyConnection())
        with pytest.raises(duckdb.Error, match="policy write failure"):
            store.replace_chunk(
                _history_metric(),
                date(2020, 1, 16),
                date(2020, 2, 14),
                [{"replacement": True}],
                ParsedRows(daily=(("steps", date(2020, 1, 20), 99.0),)),
                status=None,
                watermark=None,
                covered_start=date(2020, 1, 16),
                covered_end=date(2020, 2, 14),
                backfill_from=date(2020, 1, 16),
                history_floor=date(2020, 1, 1),
            )
        assert store.get_sync_checkpoint("steps") == old
        assert not store.history_boundary_repaired("steps", date(2020, 1, 1))
        assert (
            store.con.execute(
                "SELECT payload FROM raw_json WHERE metric='steps' AND range_start=DATE '2020-01-16'"
            ).fetchall()
            == raw
        )
        assert (
            store.con.execute("SELECT * FROM daily_series ORDER BY metric, date").fetchall()
            == daily
        )
    finally:
        store.close()


def test_repair_clips_both_floor_and_today_and_deduplicates_remaining(tmp_path):
    from health.endpoints import aligned_chunk

    store = Store(tmp_path / "health.duckdb")
    try:
        metric = _history_metric()
        start, end = aligned_chunk(date(2020, 2, 1), 30)
        store.replace_chunk(
            metric,
            start,
            end,
            [{}],
            ParsedRows(daily=(("steps", date(2020, 2, 1), 3.0), ("steps", date(2020, 2, 10), 4.0))),
            watermark=date(2020, 2, 6),
            backfill_from=start,
        )
        client = HistoryClient()
        engine = SyncEngine(
            client,
            store,
            [metric],
            today=date(2020, 2, 6),
            history_floors={"steps": date(2020, 2, 3)},
            environ={},
        )
        assert engine.history_remaining(metric) == 1
        report = engine.sync_all()
        assert client.calls == [(date(2020, 2, 3), date(2020, 2, 6))]
        assert report.history_remaining == {"steps": 0}
        assert store.history_boundary_repaired("steps", date(2020, 2, 3))
        assert store.con.execute(
            "SELECT date, value FROM daily_series WHERE date IN (DATE '2020-02-01', DATE '2020-02-10') ORDER BY date"
        ).fetchall() == [(date(2020, 2, 1), 3.0), (date(2020, 2, 10), 4.0)]
    finally:
        store.close()


def test_accurate_checkpoint_counts_repair_chunk_only_once(tmp_path):
    store = Store(tmp_path / "health.duckdb")
    try:
        _sync_history(store, HistoryClient(), date(2020, 2, 1))
        engine = SyncEngine(
            HistoryClient(),
            store,
            [_history_metric()],
            today=date(2020, 4, 30),
            history_floors={"steps": date(2020, 1, 1)},
            environ={},
        )
        # Jan 16..Feb 14 is both the repair and the next backwards chunk.
        assert engine.history_remaining(_history_metric()) == 2
    finally:
        store.close()
