import json
from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.estat import EstatRequest, ingest_estat, parse_estat_time
from market_research.fetch import FetchError
from market_research.storage import ResearchStore

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


def request(**changes):
    fields = dict(
        stats_data_id="0000000001",
        indicator="JP_SAMPLE",
        unit="人",
        frequency="monthly",
        classifications=(("tab", "01"), ("area", "00000"), ("cat01", "A")),
    )
    fields.update(changes)
    return EstatRequest(**fields)


def value(time, amount, **changes):
    result = {
        "@tab": "01",
        "@area": "00000",
        "@cat01": "A",
        "@time": time,
        "@unit": "人",
        "$": amount,
    }
    result.update(changes)
    return result


def page(values, next_key=None):
    info = {"FROM_NUMBER": 1, "TO_NUMBER": len(values)}
    if next_key is not None:
        info["NEXT_KEY"] = next_key
    return {
        "GET_STATS_DATA": {
            "RESULT": {"STATUS": 0},
            "PARAMETER": {"APP_ID": "supersecret"},
            "STATISTICAL_DATA": {
                "TABLE_INF": {"@id": "0000000001"},
                "RESULT_INF": info,
                "DATA_INF": {"VALUE": values},
            },
        }
    }


class Client:
    def __init__(self, pages, fail_at=None):
        self.pages, self.fail_at = pages, fail_at
        self.positions = []

    def get(self, url, *, params):
        assert url == "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
        self.positions.append(params["startPosition"])
        if params["startPosition"] == self.fail_at:
            raise FetchError("network")
        return json.dumps(self.pages[params["startPosition"]], ensure_ascii=False).encode()


def test_estat_pages_are_one_snapshot_with_explicit_dimension_and_unit(tmp_path):
    pages = {
        1: page([value("2026000101", "1"), value("2026000202", "2")], 3),
        3: page([value("2026000303", "3")]),
    }
    source = Client(pages)
    with ResearchStore(tmp_path) as store:
        result = ingest_estat(
            store, request(), client=source, app_id="supersecret", now=lambda: NOW, limit=2
        )
        assert source.positions == [1, 3]
        assert [row.period_start for row in result.rows] == [
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 3, 1),
        ]
        assert all(row.release_at == NOW and row.vintage_kind == "snapshot" for row in result.rows)
        assert b"supersecret" not in store.read_raw(result.snapshot)
        assert store.macro_view("JP_SAMPLE", NOW - timedelta(microseconds=1), "estat") == ()
        assert len(store.macro_view("JP_SAMPLE", NOW, "estat")) == 3


def test_estat_partial_page_resumes_without_exposing_data(tmp_path):
    pages = {
        1: page([value("2026000101", "1"), value("2026000202", "2")], 3),
        3: page([value("2026000303", "3")]),
    }
    with ResearchStore(tmp_path) as store:
        with pytest.raises(FetchError):
            ingest_estat(
                store,
                request(),
                client=Client(pages, fail_at=3),
                app_id="supersecret",
                now=lambda: NOW,
                limit=2,
            )
        assert store.macro_view("JP_SAMPLE", NOW, "estat") == ()
        assert store.pending_snapshot(request().key).cursor == "3"
        source = Client(pages)
        ingest_estat(
            store,
            request(),
            client=source,
            app_id="supersecret",
            now=lambda: NOW,
            limit=2,
            resume=True,
        )
        assert source.positions == [3]


def test_estat_rejects_unselected_dimension_and_bad_time_code(tmp_path):
    bad = page([value("2026000101", "1", **{"@cat02": "different"})])
    with ResearchStore(tmp_path) as store, pytest.raises(ValueError, match="classification"):
        ingest_estat(
            store,
            request(),
            client=Client({1: bad}),
            app_id="supersecret",
            now=lambda: NOW,
            limit=2,
        )
    assert parse_estat_time("2026000000", "annual") == date(2026, 1, 1)
    with pytest.raises(ValueError, match="time"):
        parse_estat_time("2026000000", "monthly")
    with pytest.raises(ValueError, match="time"):
        parse_estat_time("2026100000", "annual")
