import json
from datetime import UTC, date, datetime, timedelta

import pytest
from market_research.cli import main
from market_research.contracts import Instrument
from market_research.fetch import FetchError, HttpClient
from market_research.ingestion import cache_key, ingest_prices
from market_research.providers import PriceRequest
from market_research.storage import ResearchStore

NOW = datetime(2026, 9, 25, 14, tzinfo=UTC)
INST = Instrument("CRYPTO", "BTCUSDT", "USDT", "UTC")
REQUEST = PriceRequest(INST, "BTCUSDT", date(2026, 9, 24), date(2026, 9, 25))


def client():
    def transport(*_):
        rows = []
        for day in (24, 25):
            start = int(datetime(2026, 9, day, tzinfo=UTC).timestamp() * 1000)
            rows.append([start, "100", "101", "99", "100.5", "10", start + 86400000 - 1])
        return 200, {}, json.dumps(rows).encode()

    return HttpClient(transport=transport)


def test_fetch_store_reopen_query_and_exclusion(tmp_path):
    with ResearchStore(tmp_path) as store:
        result = ingest_prices(store, "binance", REQUEST, client=client(), now=lambda: NOW)
        assert not result.stale and result.error is None
        assert len(result.view.bars) == 1
        assert len(result.view.exclusions) == 1
    with ResearchStore(tmp_path) as store:
        snapshot = store.get_snapshot(result.snapshot.snapshot_id)
        view = store.snapshot_price_view(snapshot, NOW + timedelta(days=1))
        assert view == result.view


def test_failed_refresh_requires_explicit_stale_fallback(tmp_path):
    def unavailable(*_):
        return 503, {}, b""

    failed = HttpClient(transport=unavailable, sleep=lambda _: None)
    with ResearchStore(tmp_path) as store:
        initial = ingest_prices(store, "binance", REQUEST, client=client(), now=lambda: NOW)
        with pytest.raises(FetchError):
            ingest_prices(
                store, "binance", REQUEST, client=failed, now=lambda: NOW + timedelta(days=2)
            )
        result = ingest_prices(
            store,
            "binance",
            REQUEST,
            client=failed,
            now=lambda: NOW + timedelta(days=2),
            allow_stale=True,
        )
        assert result.stale and result.error == "server"
        assert result.snapshot.snapshot_id == initial.snapshot.snapshot_id


def test_cache_identity_includes_requested_window_and_provider_symbol():
    other = PriceRequest(INST, "BTCUSDT", date(2026, 9, 1), date(2026, 9, 25))
    alias = PriceRequest(INST, "XBTUSDT", REQUEST.start, REQUEST.end)
    assert len({cache_key("binance", request).digest for request in (REQUEST, other, alias)}) == 3


def test_cli_query_after_reopen_is_offline(tmp_path, capsys, monkeypatch):
    with ResearchStore(tmp_path) as store:
        result = ingest_prices(store, "binance", REQUEST, client=client(), now=lambda: NOW)

    def blocked(*_args, **_kwargs):
        raise AssertionError("query must not fetch")

    monkeypatch.setattr(HttpClient, "get", blocked)
    assert (
        main(
            [
                "--data-root",
                str(tmp_path),
                "prices",
                "--snapshot-id",
                result.snapshot.snapshot_id,
                "--as-of",
                NOW.isoformat(),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["raw_hash"] == result.snapshot.raw_hash
    assert len(payload["bars"]) == 1
    assert payload["excluded"][0]["reason"] == "non_final"


def test_partial_jquants_fetch_can_resume_without_repeating_first_page(tmp_path, monkeypatch):
    from urllib.parse import parse_qs, urlsplit

    from market_research.calendars import SessionCalendar
    from market_research.storage import CacheUnavailableError

    monkeypatch.setenv("JQUANTS_API_KEY", "fixture-token")
    inst = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
    request = PriceRequest(inst, "7203", REQUEST.start, REQUEST.end)
    calendar = SessionCalendar(
        "XTKS",
        "fixture",
        {
            date(2026, 9, day): (
                datetime(2026, 9, day, tzinfo=UTC),
                datetime(2026, 9, day, 6, 30, tzinfo=UTC),
            )
            for day in (24, 25)
        },
    )
    calls = []

    def transport(url, *_):
        cursor = parse_qs(urlsplit(url).query).get("pagination_key", [None])[0]
        calls.append(cursor)
        if cursor:
            return 503, {}, b""
        return (
            200,
            {},
            json.dumps(
                {
                    "data": [{"Date": "2026-09-24", "Code": "72030", "C": 100}],
                    "pagination_key": "next",
                }
            ).encode(),
        )

    with ResearchStore(tmp_path) as store:
        with pytest.raises(FetchError):
            ingest_prices(
                store,
                "jquants",
                request,
                calendar=calendar,
                client=HttpClient(transport=transport, sleep=lambda _: None),
                now=lambda: NOW,
            )

        def finish(url, *_):
            assert parse_qs(urlsplit(url).query)["pagination_key"] == ["next"]
            return (
                200,
                {},
                json.dumps({"data": [{"Date": "2026-09-25", "Code": "72030", "C": 101}]}).encode(),
            )

        result = ingest_prices(
            store,
            "jquants",
            request,
            calendar=calendar,
            client=HttpClient(transport=finish),
            now=lambda: NOW,
            resume=True,
        )
        assert len(result.view.bars) == 2 and result.snapshot.complete
        assert calls == [None, "next", "next", "next"]
        with pytest.raises(CacheUnavailableError):
            store.pending_snapshot(cache_key("jquants", request, calendar))


@pytest.mark.parametrize("has_trade", [True, False])
def test_no_trade_day_is_saved_as_gap_and_valid_days_remain_readable(
    tmp_path, monkeypatch, has_trade
):
    from market_research.calendars import SessionCalendar

    monkeypatch.setenv("JQUANTS_API_KEY", "fixture-token")
    instrument = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
    request = PriceRequest(instrument, "7203", REQUEST.start, REQUEST.end)
    calendar = SessionCalendar(
        "XTKS",
        "fixture",
        {
            date(2026, 9, day): (
                datetime(2026, 9, day, tzinfo=UTC),
                datetime(2026, 9, day, 6, 30, tzinfo=UTC),
            )
            for day in (24, 25)
        },
    )
    gap = {
        "Date": "2026-09-25",
        "Code": "72030",
        "O": None,
        "H": None,
        "L": None,
        "C": None,
        "Vo": None,
    }
    rows = [{"Date": "2026-09-24", "Code": "72030", "C": 100}, gap] if has_trade else [gap]
    http = HttpClient(transport=lambda *_: (200, {}, json.dumps({"data": rows}).encode()))
    with ResearchStore(tmp_path) as store:
        result = ingest_prices(
            store, "jquants", request, calendar=calendar, client=http, now=lambda: NOW
        )
        assert len(result.view.bars) == int(has_trade)
        assert len(result.view.gaps) == 1 and result.view.gaps[0].reason == "no_trade"
        assert result.view.gaps[0].session_date == date(2026, 9, 25)
    with ResearchStore(tmp_path) as store:
        assert store.snapshot_price_view(result.snapshot, NOW) == result.view


def test_resume_keeps_original_page_observation_and_partial_state(tmp_path, monkeypatch):
    from urllib.parse import parse_qs, urlsplit

    from market_research.calendars import SessionCalendar

    monkeypatch.setenv("JQUANTS_API_KEY", "fixture-token")
    instrument = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
    request = PriceRequest(instrument, "7203", date(2026, 9, 25), date(2026, 9, 25))
    calendar = SessionCalendar(
        "XTKS",
        "fixture",
        {
            date(2026, 9, 25): (
                datetime(2026, 9, 25, tzinfo=UTC),
                datetime(2026, 9, 25, 6, 30, tzinfo=UTC),
            )
        },
    )
    intraday = datetime(2026, 9, 25, 5, tzinfo=UTC)

    def first(url, *_):
        if "pagination_key" in parse_qs(urlsplit(url).query):
            return 503, {}, b""
        return (
            200,
            {},
            json.dumps(
                {
                    "data": [{"Date": "2026-09-25", "Code": "72030", "C": 100}],
                    "pagination_key": "next",
                }
            ).encode(),
        )

    with ResearchStore(tmp_path) as store:
        with pytest.raises(FetchError):
            ingest_prices(
                store,
                "jquants",
                request,
                calendar=calendar,
                client=HttpClient(transport=first, sleep=lambda _: None),
                now=lambda: intraday,
            )
        result = ingest_prices(
            store,
            "jquants",
            request,
            calendar=calendar,
            client=HttpClient(transport=lambda *_: (200, {}, b'{"data": []}')),
            now=lambda: intraday + timedelta(days=1),
            resume=True,
        )
        assert result.view.bars == ()
        assert result.view.exclusions[0].bar.observed_at == intraday
        assert result.view.exclusions[0].reason == "non_final"
