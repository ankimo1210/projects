from datetime import UTC, date, datetime

import pandas as pd
import pytest
from sector_leadlag.data.store import FetchError
from sector_leadlag.data.yf import complete_through, download, parse_csv, to_csv


def test_complete_through_waits_for_the_evening_of_each_market():
    morning_tokyo = datetime(2026, 10, 19, 1, 0, tzinfo=UTC)  # 10:00 JST, 21:00 EDT on the 18th
    assert complete_through(morning_tokyo, "jp") == date(2026, 10, 18)
    assert complete_through(morning_tokyo, "us") == date(2026, 10, 18)
    evening_tokyo = datetime(2026, 10, 19, 10, 0, tzinfo=UTC)  # 19:00 JST, 06:00 EDT
    assert complete_through(evening_tokyo, "jp") == date(2026, 10, 19)
    assert complete_through(evening_tokyo, "us") == date(2026, 10, 18)


def test_csv_keeps_the_local_date_and_drops_an_unfinished_day(yf_history):
    history = yf_history(
        ["2026-10-15", "2026-10-16", "2026-10-19"],
        open_=[100, 101, 102],
        close=[101, 102, 103],
        dividends=[0, 5, 0],
        splits=[0, 0, 2],
    )
    frame = parse_csv(to_csv(history, date(2026, 10, 16)))
    assert list(frame.index) == [pd.Timestamp("2026-10-15"), pd.Timestamp("2026-10-16")]
    assert list(frame.columns) == [
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dividends",
        "splits",
    ]
    assert frame.loc["2026-10-16", "dividends"] == 5.0


def test_download_retries_then_names_the_ticker(yf_history):
    calls: list[str] = []

    def empty(ticker: str) -> pd.DataFrame:
        calls.append(ticker)
        return pd.DataFrame()

    with pytest.raises(FetchError, match=r"1617\.T"):
        download("1617.T", attempts=3, history=empty, sleep=lambda _: None)
    assert calls == ["1617.T"] * 3

    good = yf_history(["2026-10-15"], open_=[1.0], close=[2.0], tz="America/New_York")
    content = download(
        "XLK",
        fetched_at=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        history=lambda _: good,
        sleep=lambda _: None,
    )
    assert parse_csv(content)["close"].tolist() == [2.0]
