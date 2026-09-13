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


def test_quotes_from_closes_takes_last_two_valid_closes() -> None:
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
