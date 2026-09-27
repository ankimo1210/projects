import json
from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.alfred import AlfredRequest, fetch_alfred, ingest_alfred
from market_research.contracts import MacroObservation
from market_research.fetch import FetchError
from market_research.storage import ResearchStore

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


class Pages:
    def __init__(self, pages, fail_at=None):
        self.pages, self.fail_at = pages, fail_at
        self.offsets = []

    def get(self, url, *, params):
        assert url == "https://api.stlouisfed.org/fred/series/observations"
        self.offsets.append(params["offset"])
        if params["offset"] == self.fail_at:
            raise FetchError("network")
        return json.dumps(self.pages[params["offset"]]).encode()


def page(offset, count, observations):
    return {"count": count, "offset": offset, "limit": 2, "observations": observations}


def row(period, vintage, value):
    return {"date": period, "realtime_start": vintage, "realtime_end": "9999-12-31", "value": value}


def request(**changes):
    kwargs = dict(
        series_id="GDP",
        indicator="GDP",
        start=date(2025, 1, 1),
        end=date(2025, 12, 31),
        unit="billions",
        frequency="quarterly",
        seasonal_adjustment="sa",
        realtime_start=date(2025, 4, 1),
        realtime_end=date(2026, 9, 27),
    )
    kwargs.update(changes)
    return AlfredRequest(**kwargs)


def test_paginated_revisions_use_next_ny_day_and_do_not_infer_first_vintage(tmp_path):
    pages = {
        0: page(
            0, 3, [row("2025-01-01", "2025-04-01", "100"), row("2025-01-01", "2025-07-01", "101")]
        ),
        2: page(2, 3, [row("2025-04-01", "2025-07-01", ".")]),
    }
    source = Pages(pages)
    batch = fetch_alfred(request(), client=source, api_key="secret", now=lambda: NOW, limit=2)
    assert source.offsets == [0, 2]
    assert [v.value for v in batch.rows] == [100, 101]
    assert batch.rows[0].release_at == datetime(2025, 4, 2, 4, tzinfo=UTC)
    assert batch.rows[1].release_at == datetime(2025, 7, 2, 4, tzinfo=UTC)
    assert batch.rows[0].source_release_date == date(2025, 4, 1)
    assert batch.rows[0].vintage_kind == "estimated"
    assert batch.rows[0].vintage_id == "2025-04-01"
    assert b"secret" not in batch.raw
    with ResearchStore(tmp_path) as store:
        store.save(batch.key, batch.raw, observed_at=NOW, macro=batch.rows)
        assert store.macro_view("GDP", datetime(2025, 4, 2, 3, tzinfo=UTC), "alfred") == ()
        assert (
            store.macro_view("GDP", datetime(2025, 4, 2, 4, tzinfo=UTC), "alfred")[0].value == 100
        )


def test_winter_release_boundary_and_narrow_window_do_not_make_vintage_one():
    source = Pages({0: page(0, 1, [row("2025-01-01", "2025-12-01", "102")])})
    batch = fetch_alfred(
        request(realtime_start=date(2025, 12, 1)),
        client=source,
        api_key="secret",
        now=lambda: NOW,
        limit=2,
    )
    assert batch.rows[0].release_at == datetime(2025, 12, 2, 5, tzinfo=UTC)
    assert batch.rows[0].vintage_id == "2025-12-01"
    assert not hasattr(batch.rows[0], "vintage_seq")


def test_partial_pages_are_returned_for_resume_without_publishing(tmp_path):
    pages = {
        0: page(
            0, 3, [row("2025-01-01", "2025-04-01", "100"), row("2025-01-01", "2025-07-01", "101")]
        ),
        2: page(2, 3, [row("2025-04-01", "2025-07-01", "200")]),
    }
    failing = Pages(pages, fail_at=2)
    with pytest.raises(FetchError) as exc:
        fetch_alfred(request(), client=failing, api_key="secret", now=lambda: NOW, limit=2)
    assert exc.value.cursor == "2"
    assert b"secret" not in exc.value.partial_raw
    recovered = Pages(pages)
    batch = fetch_alfred(
        request(),
        client=recovered,
        api_key="secret",
        now=lambda: NOW,
        limit=2,
        resume_raw=exc.value.partial_raw,
    )
    assert recovered.offsets == [2]
    assert len(batch.rows) == 3
    with ResearchStore(tmp_path) as store:
        pending = store.save(
            batch.key, exc.value.partial_raw, observed_at=NOW, complete=False, cursor="2"
        )
        assert store.macro_view("GDP", NOW, "alfred") == ()
        assert store.read_raw(pending) == exc.value.partial_raw
        store.save(batch.key, batch.raw, observed_at=NOW + timedelta(seconds=1), macro=batch.rows)
        assert len(store.macro_view("GDP", NOW, "alfred")) == 2


def test_ingest_keeps_partial_private_then_resumes_and_stale_is_explicit(tmp_path):
    pages = {
        0: page(
            0, 3, [row("2025-01-01", "2025-04-01", "100"), row("2025-01-01", "2025-07-01", "101")]
        ),
        2: page(2, 3, [row("2025-04-01", "2025-07-01", "200")]),
    }
    with ResearchStore(tmp_path) as store:
        with pytest.raises(FetchError):
            ingest_alfred(
                store,
                request(),
                client=Pages(pages, fail_at=2),
                api_key="secret",
                now=lambda: NOW,
                limit=2,
            )
        assert store.macro_view("GDP", NOW, "alfred") == ()
        assert store.pending_snapshot(request().key).cursor == "2"
        source = Pages(pages)
        completed = ingest_alfred(
            store,
            request(),
            client=source,
            api_key="secret",
            now=lambda: NOW + timedelta(seconds=1),
            limit=2,
            resume=True,
        )
        assert source.offsets == [2]
        assert len(completed.rows) == 2
        assert not completed.stale
        stale = ingest_alfred(
            store,
            request(),
            client=Pages(pages, fail_at=0),
            api_key="secret",
            now=lambda: NOW + timedelta(days=2),
            limit=2,
            allow_stale=True,
        )
        assert stale.stale and stale.error == "network"
        assert stale.snapshot.snapshot_id == completed.snapshot.snapshot_id


def test_ingest_result_is_scoped_to_its_requested_snapshot(tmp_path):
    source = Pages({0: page(0, 1, [row("2025-01-01", "2025-04-01", "100")])})
    unrelated = MacroObservation(
        "GDP", date(2024, 1, 1), NOW - timedelta(days=2), 999, "alfred", "unrelated"
    )
    with ResearchStore(tmp_path) as store:
        other_key = request(series_id="OTHER").key
        store.save(other_key, b"other", observed_at=NOW, macro=(unrelated,))
        result = ingest_alfred(
            store, request(), client=source, api_key="secret", now=lambda: NOW, limit=2
        )
        assert [item.period_start for item in result.rows] == [date(2025, 1, 1)]
