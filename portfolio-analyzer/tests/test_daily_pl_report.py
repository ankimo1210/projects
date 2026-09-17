"""Offline tests for the daily P&L report script (no network)."""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "daily_pl_report", PROJECT_ROOT / "scripts/daily_pl_report.py"
)
daily_pl_report = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(daily_pl_report)


def test_quotes_from_closes_compares_the_last_two_dates_of_the_shared_calendar() -> None:
    idx = pd.to_datetime(["2026-09-08", "2026-09-09", "2026-09-10", "2026-09-11"])
    closes = pd.DataFrame(
        {"1329.T": [7000.0, 7050.0, float("nan"), 7100.0], "XLE": [63.0, 63.5, 64.0, float("nan")]},
        index=idx,
    )
    quotes = daily_pl_report.quotes_from_closes(closes)
    assert quotes["1329.T"].close == Decimal("7100.0") and quotes["1329.T"].date == "2026-09-11"
    assert (
        quotes["1329.T"].prev_close == Decimal("7050.0")
        and quotes["1329.T"].prev_date == "2026-09-09"
    )
    assert quotes["XLE"].close == Decimal("64.0") and quotes["XLE"].date == "2026-09-10"
    # XLE did not trade on the last date, so it has not moved since the one before
    assert quotes["XLE"].prev_close == Decimal("64.0") and quotes["XLE"].prev_date == "2026-09-10"


def test_quotes_from_closes_does_not_repeat_a_closed_market_s_last_move() -> None:
    # Evening in Tokyo: Monday's yen closes and USD/JPY are in, New York has not opened.
    idx = pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-14"])
    closes = pd.DataFrame(
        {
            "6857.T": [33920.0, 31720.0, 31080.0],
            "SMH": [560.28, 568.53, float("nan")],
            "JPY=X": [153.2, 153.64, 154.87],
        },
        index=idx,
    )
    quotes = daily_pl_report.quotes_from_closes(closes)
    assert quotes["6857.T"].prev_close == Decimal("31720.0")
    smh = quotes["SMH"]
    # Friday's move was Friday's report; today SMH has no move of its own, only the rate's
    assert smh.close == smh.prev_close == Decimal("568.53")
    assert smh.date == "2026-09-11" and smh.prev_date == "2026-09-11"
    assert quotes["JPY=X"].prev_close == Decimal("153.64")


def test_quotes_from_closes_catches_up_the_whole_move_after_a_holiday() -> None:
    # Tokyo shut on Monday 09-21: Tuesday's report carries Friday → Tuesday once.
    idx = pd.to_datetime(["2026-09-18", "2026-09-21", "2026-09-22"])
    closes = pd.DataFrame(
        {"1329.T": [6600.0, float("nan"), 6700.0], "XLE": [65.0, 66.0, 67.0]}, index=idx
    )
    q = daily_pl_report.quotes_from_closes(closes)["1329.T"]
    assert q.close == Decimal("6700.0") and q.prev_close == Decimal("6600.0")
    assert q.prev_date == "2026-09-18"


def test_quotes_from_closes_ignores_dates_none_of_its_columns_trade() -> None:
    idx = pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-12"])
    closes = pd.DataFrame({"XLE": [64.0, 65.0, float("nan")]}, index=idx)
    q = daily_pl_report.quotes_from_closes(closes)["XLE"]
    assert q.close == Decimal("65.0") and q.prev_close == Decimal("64.0")


def test_quotes_from_closes_single_point_has_no_previous() -> None:
    closes = pd.DataFrame({"QQQ": [730.0]}, index=pd.to_datetime(["2026-09-11"]))
    q = daily_pl_report.quotes_from_closes(closes)["QQQ"]
    assert q.prev_close is None and q.prev_date is None


def test_report_as_of_is_latest_quote_date() -> None:
    from portfolio_analyzer.mtm import Quote

    quotes = {
        "1329.T": Quote(Decimal(1), Decimal(1), "2026-09-11", "2026-09-10"),
        "XLE": Quote(Decimal(1), Decimal(1), "2026-09-10", "2026-09-09"),
    }
    assert daily_pl_report.report_as_of(quotes) == "2026-09-11"
    assert daily_pl_report.stale_quotes(quotes, "2026-09-11") == {"XLE": "2026-09-10"}


def test_add_series_joins_a_fund_price_onto_the_closes_by_date() -> None:
    idx = pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-12"])
    closes = pd.DataFrame({"XLE": [64.0, 65.0, 65.5]}, index=idx)
    points = [
        ("2026-09-01", Decimal("26000")),  # before the frame starts: dropped
        ("2026-09-10", Decimal("25962")),
        ("2026-09-11", Decimal("25885")),
    ]
    out = daily_pl_report.add_series(closes, "SOMPO_AM:0885", points)
    assert list(out.index) == list(idx)
    assert out["SOMPO_AM:0885"].iloc[1] == 25885.0 and out["SOMPO_AM:0885"].isna().iloc[2]
    q = daily_pl_report.quotes_from_closes(out[["SOMPO_AM:0885"]])["SOMPO_AM:0885"]
    assert q.close == Decimal("25885.0") and q.prev_close == Decimal("25962.0")


def test_attribution_of_buckets_the_window_and_inception() -> None:
    from portfolio_analyzer import timeseries as ts

    s = ts.AccountSeries(
        account_id="a",
        nav=[None, Decimal(110), Decimal(130)],
        deposits_cum=[None, Decimal(100), Decimal(100)],
        unrealized=[None, Decimal(6), Decimal(20)],
        realized_cum=[None, Decimal(1), Decimal(4)],
        dividends_cum=[None, Decimal(3), Decimal(6)],
        fees_cum=[None, Decimal(0), Decimal(0)],
        fx_translation_cum=[None, Decimal(0), Decimal(0)],
        forex_cum=[None, Decimal(0), Decimal(0)],
    )
    out = daily_pl_report.attribution_of(s, wi=1)
    assert out["window"] == {
        "unrealized": 14.0,
        "realized": 3.0,
        "dividends": 3.0,
        "fees": 0.0,
        "fx_translation": 0.0,
        "forex": 0.0,
        "total": 20.0,
    }
    assert out["incept"]["total"] == 30.0 and out["incept"]["unrealized"] == 20.0
    # a window that starts before the series is defined measures from its first defined date
    assert daily_pl_report.attribution_of(s, wi=0)["window"]["total"] == 20.0


def test_history_start_reaches_back_to_the_oldest_episode() -> None:
    from datetime import date

    episodes = [
        {"start": "2024-07-31", "end": "2024-08-05"},
        {"start": "2025-04-02", "end": "2025-04-08"},
    ]
    assert daily_pl_report.history_start(date(2026, 9, 15), 760, episodes) == "2024-07-24"
    assert daily_pl_report.history_start(date(2026, 9, 15), 760, []) == "2024-08-16"


def test_jpy_price_paths_convert_dollar_tickers_and_daily_returns_skip_gaps() -> None:
    idx = pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-14"])
    filled = pd.DataFrame(
        {
            "SMH": [560.0, 568.0, 568.0],
            "6857.T": [float("nan"), 31720.0, 31080.0],
            "JPY=X": [153.0, 154.0, 155.0],
        },
        index=idx,
    )
    paths = daily_pl_report.jpy_price_paths(filled, ["SMH", "6857.T", "GONE"], "JPY=X", {"SMH"})
    assert paths["SMH"] == [560.0 * 153.0, 568.0 * 154.0, 568.0 * 155.0]
    assert paths["6857.T"][0] is None and paths["6857.T"][1] == 31720.0 and "GONE" not in paths
    assert daily_pl_report.daily_returns(paths["6857.T"]) == [
        0.0,
        0.0,
        pytest.approx(31080.0 / 31720.0 - 1),
    ]


def test_clean_closes_blanks_a_misprint_run_but_keeps_a_level_the_series_holds() -> None:
    idx = pd.to_datetime([f"2026-03-{d:02d}" for d in range(24, 32)])
    closes = pd.DataFrame(
        {
            # a two-day tenfold misprint, then back to the old level (1306.T, 2026-03-30/31)
            "1306.T": [380.0, 382.0, 382.7, float("nan"), 37.6, 37.1, 389.2, 383.0],
            # a split-like drop the series keeps is not a misprint
            "SPLIT": [1000.0, 1010.0, 101.0, 102.0, 103.0, 101.5, 100.0, 99.0],
            "FLAT": [1.0] * 8,
        },
        index=idx,
    )
    cleaned, dropped = daily_pl_report.clean_closes(closes)
    assert dropped == {"1306.T": ["2026-03-28", "2026-03-29"]}
    assert cleaned["1306.T"].isna().tolist() == [
        False,
        False,
        False,
        True,
        True,
        True,
        False,
        False,
    ]
    assert cleaned["SPLIT"].tolist() == closes["SPLIT"].tolist()
    assert cleaned["FLAT"].notna().all()


def test_drop_live_bars_blanks_only_today_s_unfinished_bars() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    idx = pd.to_datetime(["2026-09-15", "2026-09-16"])
    closes = pd.DataFrame(
        {"6857.T": [30160.0, 30700.0], "SMH": [542.11, 550.22], "JPY=X": [154.38, 155.10]},
        index=idx,
    )
    now = datetime(2026, 9, 16, 23, 50, tzinfo=ZoneInfo("Asia/Tokyo"))
    kept, dropped = daily_pl_report.drop_live_bars(closes, now)
    assert dropped == {"SMH": "2026-09-16"}
    assert kept["SMH"].isna().tolist() == [False, True]
    assert kept["6857.T"].tolist() == closes["6857.T"].tolist()
    assert kept["JPY=X"].tolist() == closes["JPY=X"].tolist()
    assert closes["SMH"].notna().all()  # the input is left alone
