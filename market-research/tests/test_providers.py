import json
from datetime import UTC, date, datetime

import pandas as pd
import pytest
from market_research.calendars import SessionCalendar
from market_research.contracts import Instrument
from market_research.fetch import FetchError, HttpClient
from market_research.providers import PriceRequest, fetch_prices

NOW = datetime(2026, 9, 25, 5, tzinfo=UTC)
INST = Instrument("XTKS", "7203", "JPY", "Asia/Tokyo")
CAL = SessionCalendar(
    "XTKS",
    "test-v1",
    {
        date(2026, 9, 24): (
            datetime(2026, 9, 24, tzinfo=UTC),
            datetime(2026, 9, 24, 6, 30, tzinfo=UTC),
        ),
        date(2026, 9, 25): (
            datetime(2026, 9, 25, tzinfo=UTC),
            datetime(2026, 9, 25, 6, 30, tzinfo=UTC),
        ),
    },
)


def client_for(payloads, calls):
    def transport(url, headers, timeout):
        calls.append((url, headers))
        body = payloads.pop(0)
        return 200, {}, body if isinstance(body, bytes) else json.dumps(body).encode()

    return HttpClient(transport=transport, sleep=lambda _: None)


def test_yfinance_fetch_is_raw_and_retains_open_day():
    calls = []

    def history(symbol, start, end):
        calls.append((symbol, start, end))
        return pd.DataFrame(
            {"Close": [100.0, 101.0], "Adj Close": [90.0, 91.0]},
            index=pd.DatetimeIndex(["2026-09-24", "2026-09-25"], tz="Asia/Tokyo"),
        )

    request = PriceRequest(INST, "7203.T", date(2026, 9, 24), date(2026, 9, 25), "raw")
    batch = fetch_prices("yfinance", request, calendar=CAL, now=lambda: NOW, history=history)
    assert [row.close for row in batch.bars] == [100, 101]
    assert [row.is_final for row in batch.bars] == [True, False]
    assert calls[0][2] == date(2026, 9, 26)
    assert batch.raw


def test_stooq_never_claims_raw_adjustment():
    request = PriceRequest(INST, "7203.jp", date(2026, 9, 24), date(2026, 9, 24), "unknown")
    client = client_for([b"Date,Open,High,Low,Close,Volume\n2026-09-24,99,101,98,100,20\n"], [])
    batch = fetch_prices("stooq", request, calendar=CAL, now=lambda: NOW, client=client)
    assert batch.bars[0].adjustment == "unknown"
    assert batch.bars[0].provider == "stooq"


def test_jquants_v2_pagination_and_explicit_split_adjustment(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_KEY", "fixture-token")
    request = PriceRequest(INST, "7203", date(2026, 9, 24), date(2026, 9, 25), "split")
    calls = []
    pages = [
        {
            "data": [{"Date": "2026-09-24", "Code": "72030", "C": 100, "AdjC": 50}],
            "pagination_key": "next",
        },
        {"data": [{"Date": "2026-09-25", "Code": "72030", "C": 101, "AdjC": 51}]},
    ]
    batch = fetch_prices(
        "jquants", request, calendar=CAL, now=lambda: NOW, client=client_for(pages, calls)
    )
    assert [row.close for row in batch.bars] == [50, 51]
    assert calls[0][1]["x-api-key"] == "fixture-token"
    assert "pagination_key=next" in calls[1][0]
    assert b"fixture-token" not in batch.raw


def test_jquants_repeated_cursor_is_incomplete_error(monkeypatch):
    monkeypatch.setenv("JQUANTS_API_KEY", "fixture-token")
    request = PriceRequest(INST, "7203", date(2026, 9, 24), date(2026, 9, 25), "raw")
    page = {"data": [{"Date": "2026-09-24", "Code": "72030", "C": 100}], "pagination_key": "same"}
    with pytest.raises(FetchError, match="pagination"):
        fetch_prices(
            "jquants", request, calendar=CAL, now=lambda: NOW, client=client_for([page, page], [])
        )


def test_binance_daily_bar_end_and_open_candle():
    inst = Instrument("CRYPTO", "BTCUSDT", "USDT", "UTC")
    start = int(datetime(2026, 9, 25, tzinfo=UTC).timestamp() * 1000)
    row = [start, "100", "101", "99", "100.5", "20", start + 86400000 - 1, "0", 1, "0", "0", "0"]
    batch = fetch_prices(
        "binance",
        PriceRequest(inst, "BTCUSDT", date(2026, 9, 25), date(2026, 9, 25), "raw"),
        now=lambda: NOW,
        client=client_for([[row]], []),
    )
    assert not batch.bars[0].is_final
    assert batch.bars[0].bar_end == datetime(2026, 9, 26, tzinfo=UTC)
