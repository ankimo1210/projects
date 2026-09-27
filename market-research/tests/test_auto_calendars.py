import json
from datetime import UTC, date, datetime

import pandas as pd
import pytest
from market_research.calendars import auto_session_calendar
from market_research.cli import main
from market_research.contracts import Instrument
from market_research.fetch import FetchError
from market_research.ingestion import ingest_prices
from market_research.providers import PriceRequest
from market_research.storage import ResearchStore


def test_nyse_auto_calendar_preserves_dst_holiday_and_early_close():
    calendar = auto_session_calendar("XNYS", date(2026, 3, 6), date(2026, 11, 27))
    assert calendar.version.startswith("exchange-calendars/")
    assert calendar.sessions[date(2026, 3, 6)][1] == datetime(2026, 3, 6, 21, tzinfo=UTC)
    assert calendar.sessions[date(2026, 3, 9)][1] == datetime(2026, 3, 9, 20, tzinfo=UTC)
    assert date(2026, 11, 26) not in calendar.sessions
    assert calendar.sessions[date(2026, 11, 27)][1] == datetime(2026, 11, 27, 18, tzinfo=UTC)


def test_tse_auto_calendar_uses_post_2024_close_and_excludes_holiday():
    calendar = auto_session_calendar("XTKS", date(2026, 9, 23), date(2026, 9, 25))
    assert date(2026, 9, 23) not in calendar.sessions
    assert calendar.sessions[date(2026, 9, 24)] == (
        datetime(2026, 9, 24, tzinfo=UTC),
        datetime(2026, 9, 24, 6, 30, tzinfo=UTC),
    )


def test_nasdaq_market_keeps_its_identity_when_using_us_calendar_alias():
    calendar = auto_session_calendar("XNAS", date(2026, 9, 24), date(2026, 9, 25))
    assert calendar.market == "XNAS"
    assert calendar.sessions[date(2026, 9, 24)][1] == datetime(2026, 9, 24, 20, tzinfo=UTC)


def test_auto_calendar_rejects_unsupported_or_sessionless_ranges():
    with pytest.raises(ValueError, match="automatic calendar"):
        auto_session_calendar("FX", date(2026, 9, 24), date(2026, 9, 25))
    with pytest.raises(ValueError, match="no exchange sessions"):
        auto_session_calendar("XNYS", date(2026, 11, 26), date(2026, 11, 26))


def test_cli_fetch_prices_resolves_exchange_calendar_without_json(tmp_path, monkeypatch, capsys):
    frame = pd.DataFrame(
        {"Close": [100.0]},
        index=pd.DatetimeIndex(["2025-09-24"], tz="America/New_York"),
    )
    monkeypatch.setattr("market_research.providers._history", lambda *_: frame)
    code = main(
        [
            "--data-root",
            str(tmp_path),
            "fetch-prices",
            "--provider",
            "yfinance",
            "--market",
            "XNYS",
            "--symbol",
            "IBM",
            "--provider-symbol",
            "IBM",
            "--currency",
            "USD",
            "--timezone",
            "America/New_York",
            "--adjustment",
            "raw",
            "--start",
            "2025-09-24",
            "--end",
            "2025-09-24",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["bars"]) == 1
    with ResearchStore(tmp_path) as store:
        saved = store.get_snapshot(payload["snapshot_id"])
        assert "exchange-calendars/" in saved.key.request_json
        assert saved.key.request_json.count("2025-09-24") >= 1


def test_explicit_calendar_remains_authoritative(tmp_path, monkeypatch):
    from market_research.calendars import SessionCalendar

    frame = pd.DataFrame(
        {"Close": [100.0]},
        index=pd.DatetimeIndex(["2025-09-24"], tz="Asia/Tokyo"),
    )
    monkeypatch.setattr("market_research.providers._history", lambda *_: frame)
    manual = SessionCalendar(
        "XTKS",
        "manual-fixture",
        {
            date(2025, 9, 24): (
                datetime(2025, 9, 24, tzinfo=UTC),
                datetime(2025, 9, 24, 6, tzinfo=UTC),
            )
        },
    )
    request = PriceRequest(
        Instrument("XTKS", "7203", "JPY", "Asia/Tokyo"),
        "7203.T",
        date(2025, 9, 24),
        date(2025, 9, 24),
    )
    with ResearchStore(tmp_path) as store:
        result = ingest_prices(store, "yfinance", request, calendar=manual)
        assert result.view.bars[0].bar_end == datetime(2025, 9, 24, 6, tzinfo=UTC)
        assert "manual-fixture" in result.snapshot.key.request_json


def test_auto_calendar_rejects_a_provider_row_on_exchange_holiday(tmp_path, monkeypatch):
    frame = pd.DataFrame(
        {"Close": [100.0]},
        index=pd.DatetimeIndex(["2026-11-26"], tz="America/New_York"),
    )
    monkeypatch.setattr("market_research.providers._history", lambda *_: frame)
    request = PriceRequest(
        Instrument("XNYS", "IBM", "USD", "America/New_York"),
        "IBM",
        date(2026, 11, 26),
        date(2026, 11, 27),
    )
    with ResearchStore(tmp_path) as store, pytest.raises(FetchError, match="schema_or_calendar"):
        ingest_prices(store, "yfinance", request)
