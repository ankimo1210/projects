"""Offline tests for the daily P&L report script (no network)."""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

import pandas as pd

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
