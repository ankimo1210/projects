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
    # An unknown window start cannot be silently replaced by a later date.
    assert daily_pl_report.attribution_of(s, wi=0)["window"]["total"] is None


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
        None,
        None,
        pytest.approx(31080.0 / 31720.0 - 1),
    ]


@pytest.mark.parametrize(
    ("prices", "expected"),
    [
        ([], []),
        ([100.0], [None]),
        ([None, 100.0, 100.0, 110.0], [None, None, 0.0, pytest.approx(0.1)]),
        ([100.0, None, 110.0], [None, None, None]),
        ([0.0, 100.0], [None, None]),
        ([100.0, float("inf"), 110.0], [None, None, None]),
    ],
)
def test_daily_returns_preserves_unknown_history_and_real_unchanged_prices(
    prices, expected
) -> None:
    assert daily_pl_report.daily_returns(prices) == expected


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


def _offline_payload(
    tmp_path,
    monkeypatch,
    *,
    fx_adjustment=False,
    dc_available=True,
    factor_model=None,
    fx_only_last_day=False,
    ibkr_available=True,
    benchmark_only_last_day=False,
    foreign_without_history=False,
):
    """Exercise the full calculation with real ledgers and only remote prices replaced."""
    import argparse
    import json

    cash = 950 if fx_adjustment else 900
    snapshot = {
        "base_currency": "JPY",
        "accounts": [
            {"id": "gb", "name": "Broker", "as_of": "2026-09-10", "total_value_jpy": cash + 100},
            {"id": "dc", "name": "DC", "as_of": "2026-09-10", "total_value_jpy": 200},
        ],
        "positions": [
            {
                "account_id": "gb",
                "symbol": "1329",
                "name": "ETF",
                "asset_class": "日本株",
                "currency": "JPY",
                "quantity": 1,
                "price": 100,
                "fx_rate": 1,
                "market_value_jpy": 100,
            },
            {
                "account_id": "gb",
                "symbol": "CASH_JPY",
                "name": "Cash",
                "asset_class": "現金",
                "currency": "JPY",
                "quantity": None,
                "price": None,
                "fx_rate": 1,
                "market_value_jpy": cash,
            },
            {
                "account_id": "dc",
                "symbol": "FUND",
                "name": "Fund",
                "asset_class": "バランス型",
                "currency": "JPY",
                "quantity": None,
                "price": None,
                "fx_rate": 1,
                "market_value_jpy": 200,
            },
        ],
    }
    ledger = {
        "account_id": "gb",
        "holdings": [
            {
                "symbol": "1329",
                "currency": "JPY",
                "quantity": 1,
                "average_cost": 100,
                "average_trade_fx": 1,
                "cost_basis_jpy": 100,
                "commission_jpy": 0,
            }
        ],
        "closed": [],
    }
    holding = {
        "account_id": "dc",
        "symbol": "FUND",
        "ticker": "FUND:1",
        "nav_csv_url": "https://example.invalid/nav",
        "anchor": {"as_of": "2026-09-10", "units": 10000, "contributions_jpy": 200},
    }
    if foreign_without_history:
        snapshot["positions"][0].update(
            symbol="SMH", currency="USD", fx_rate=150, market_value_jpy=15000
        )
        ledger["holdings"] = []
    for name, content in (("snapshot", snapshot), ("ledger", ledger), ("dc_holding", holding)):
        (tmp_path / name).write_text(json.dumps(content), encoding="utf-8")
    transactions = "Transaction History,Header,Date,Account,Description,Transaction Type,Symbol,Quantity,価格,Price Currency,Gross Amount,Commission,Net Amount\n"
    if fx_adjustment:
        transactions += "Transaction History,Data,2026-09-11,test,FX Translations P&L,Adjustment,-,-,-,-,50,-,50\n"
    transactions += "Transaction History,Data,2026-09-10,test,ETF,Buy,1329.T,1,100,JPY,-100,0,-100\nTransaction History,Data,2026-09-10,test,Deposit,Deposit,-,-,-,-,1000,-,1000\n"
    if ibkr_available:
        (tmp_path / "transactions").write_text(transactions, encoding="utf-8")
    (tmp_path / "dc_transactions").write_text(
        "2026/09/10\t2026/09/11\tFund\t10000\t0.02\t200\t買 掛金\n", encoding="utf-8"
    )
    if factor_model is not None:
        (tmp_path / "data").mkdir()
        (tmp_path / "data/factor_estimates.json").write_text(
            json.dumps(factor_model), encoding="utf-8"
        )
        (tmp_path / "reference").write_text(
            json.dumps(
                {
                    "scenarios": [
                        {"id": "measured", "kind": "historical", "shocks": {"market": -0.1}}
                    ]
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(daily_pl_report, "PROJECT_ROOT", tmp_path)
    closes = pd.DataFrame(
        {"1329.T": [100.0, 110.0], "JPY=X": [150.0, 150.0]},
        index=pd.to_datetime(["2026-09-10", "2026-09-11"]),
    )
    if fx_only_last_day:
        closes.loc[pd.Timestamp("2026-09-14")] = [float("nan"), 151.0]
    if benchmark_only_last_day:
        closes["SPY"] = [20.0, 20.0]
        closes.loc[pd.Timestamp("2026-09-14")] = [float("nan"), float("nan"), 21.0]
    if foreign_without_history:
        closes = closes.rename(columns={"1329.T": "SMH"})
        closes.iloc[0, closes.columns.get_loc("JPY=X")] = float("nan")
    monkeypatch.setattr(daily_pl_report, "download_closes", lambda *args: closes)

    def fund_prices(url):
        if not dc_available:
            raise OSError("offline fund")
        return [("2026-09-10", Decimal(200)), ("2026-09-11", Decimal(200))]

    monkeypatch.setattr(daily_pl_report, "fetch_nav", fund_prices)
    args = argparse.Namespace(
        **{
            name: str(tmp_path / name)
            for name in (
                "snapshot",
                "ledger",
                "transactions",
                "dc_holding",
                "dc_transactions",
                "history",
                "reference",
            )
        },
        jp_transactions=str(tmp_path / "missing-jp"),
        jp_account="securities",
        history_days=760,
        window_days=1,
        edition="",
    )
    return daily_pl_report.build_payload(args)[0]


def test_daily_rate_uses_total_nav_including_cash_and_unquoted_assets(
    tmp_path, monkeypatch
) -> None:
    payload = _offline_payload(tmp_path, monkeypatch)
    assert payload["headline"]["day_pnl"] == 10.0
    assert payload["headline"]["day_pnl_pct"] == pytest.approx(100 / 120)


def test_fx_statement_adjustment_does_not_become_exact_period_return(tmp_path, monkeypatch) -> None:
    payload = _offline_payload(tmp_path, monkeypatch, fx_adjustment=True)
    assert payload["headline"]["pnl_incept"] == 60.0
    assert payload["headline"]["pnl_window"] is None
    assert payload["headline"]["max_dd_window"] is None
    assert payload["series"]["daily_pnl"] == [None, None]
    assert payload["headline"]["xirr_is_estimate"] is True


def test_unavailable_dc_prices_keep_the_account_and_propagate_unknown_total(
    tmp_path, monkeypatch
) -> None:
    payload = _offline_payload(tmp_path, monkeypatch, dc_available=False)
    assert "dc" in payload["series"]["accounts"]
    assert payload["series"]["nav"] == [None, None]
    assert payload["headline"]["pnl_incept"] is None
    assert payload["headline"]["pnl_window"] is None
    assert payload["quality"]["accounts_expected"] == ["gb", "dc"]


def test_daily_report_uses_the_compatible_joint_factor_model(tmp_path, monkeypatch) -> None:
    model = {
        "factor_risk": {
            "factors": ["market"],
            "covariance": [[0.01]],
            "observations": 10,
            "frequency": "weekly",
        },
        "measured_factor_model": {
            "basis": "joint-jpy-excess-v1",
            "factors": ["market"],
            "instruments": {
                "1329": {"loadings": {"market": 1}},
                "FUND": {"loadings": {"market": 0}},
            },
        },
    }
    payload = _offline_payload(tmp_path, monkeypatch, factor_model=model)
    scenario = payload["risk"]["stress"]["scenarios"][0]
    assert scenario["impact_jpy"] == -11.0
    assert scenario["model_basis"] == "measured_joint"


def test_daily_report_preserves_incomplete_returns_through_risk_statistics(
    tmp_path, monkeypatch
) -> None:
    model = {
        "factor_risk": {
            "factors": ["market"],
            "covariance": [[0.01]],
            "observations": 10,
            "frequency": "weekly",
        }
    }
    payload = _offline_payload(tmp_path, monkeypatch, factor_model=model)
    stats = payload["risk"]["stats"]
    assert stats["vol_annual"] is None and stats["var_1d_95"] is None
    assert stats["coverage_ratio"] == 0.0 and stats["reason"]
    assert payload["risk"]["contributions"]["positions"] == []


def test_jpy_price_path_does_not_backfill_an_unknown_historical_fx_rate() -> None:
    filled = pd.DataFrame({"SMH": [100.0, 100.0], "JPY=X": [float("nan"), 150.0]})
    paths = daily_pl_report.jpy_price_paths(filled, ["SMH"], "JPY=X", {"SMH"})
    assert paths["SMH"] == [None, 15000.0]


def test_report_date_matches_the_last_valuation_when_only_fx_has_a_new_bar(
    tmp_path, monkeypatch
) -> None:
    payload = _offline_payload(tmp_path, monkeypatch, fx_only_last_day=True)
    assert payload["as_of"] == "2026-09-14"
    assert payload["window"]["end"] == payload["series"]["dates"][-1]


def test_missing_ibkr_history_is_not_a_zero_balance_account(tmp_path, monkeypatch) -> None:
    payload = _offline_payload(tmp_path, monkeypatch, ibkr_available=False)
    assert payload["series"]["accounts"]["gb"]["nav"] == [None, None]
    assert payload["headline"]["pnl_incept"] is None
    assert payload["quality"]["accounts_available"] == ["dc"]


def test_benchmark_dates_after_the_latest_valuation_do_not_extend_account_history(
    tmp_path, monkeypatch
) -> None:
    payload = _offline_payload(tmp_path, monkeypatch, benchmark_only_last_day=True)
    assert payload["as_of"] == "2026-09-11"
    assert payload["series"]["dates"][-1] == "2026-09-11"


def test_a_foreign_value_card_waits_for_a_known_fx_baseline(tmp_path, monkeypatch) -> None:
    payload = _offline_payload(
        tmp_path, monkeypatch, ibkr_available=False, foreign_without_history=True
    )
    assert payload["series"]["symbols"]["SMH@gb"]["pnl"] == [None, 0.0]


def test_console_summary_distinguishes_unknown_pnl_from_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["daily_pl_report.py"])
    args = daily_pl_report.parse_args()
    args.out_dir = str(tmp_path / "reports")
    args.history = str(tmp_path / "history.jsonl")
    monkeypatch.setattr(daily_pl_report, "parse_args", lambda: args)
    payload = {
        "fx": {"last": 150},
        "positions": [],
        "headline": {
            "nav_total": 100,
            "day_pnl": 0,
            "pnl_window": None,
            "pnl_incept": None,
            "unrealized_known": 0,
        },
    }
    monkeypatch.setattr(daily_pl_report, "build_payload", lambda _: (payload, {}, "2026-10-08"))
    monkeypatch.setattr(daily_pl_report.mtm, "upsert_history", lambda *_: [])
    monkeypatch.setattr(daily_pl_report.dashboard, "render", lambda *_: "<html></html>")
    assert daily_pl_report.main() == 0
    output = capsys.readouterr().out
    assert "window 未計算" in output and "inception 未計算" in output
    assert "day +0" in output


@pytest.mark.parametrize("email_requested", [False, True])
def test_console_position_with_unknown_day_change_does_not_fail_the_job(
    tmp_path, monkeypatch, capsys, email_requested
) -> None:
    monkeypatch.setattr("sys.argv", ["daily_pl_report.py"])
    args = daily_pl_report.parse_args()
    args.out_dir = str(tmp_path / "reports")
    args.history = str(tmp_path / "history.jsonl")
    args.email = ["unit@example.invalid"] if email_requested else None
    args.no_image = True
    monkeypatch.setattr(daily_pl_report, "parse_args", lambda: args)
    payload = {
        "fx": {"last": 150},
        "positions": [{"sym": "SMH", "acct": "Broker", "last": 100, "chg1d": None, "value": 15000}],
        "headline": {
            "nav_total": 15000,
            "day_pnl": None,
            "pnl_window": None,
            "pnl_incept": None,
            "unrealized_known": None,
        },
    }
    monkeypatch.setattr(daily_pl_report, "build_payload", lambda _: (payload, {}, "2026-10-08"))
    monkeypatch.setattr(daily_pl_report.mtm, "upsert_history", lambda *_: [])
    monkeypatch.setattr(daily_pl_report.dashboard, "render", lambda *_: "<html></html>")
    # Exercise the post-email console path while all external sending is replaced.
    monkeypatch.setenv("PL_SMTP_USER", "unit@example.invalid")
    monkeypatch.setenv("PL_SMTP_PASS", "unit-test-only")
    monkeypatch.setattr(daily_pl_report.mailer, "build_message", lambda *args, **kwargs: object())
    monkeypatch.setattr(daily_pl_report.mailer, "send", lambda *args, **kwargs: None)
    assert daily_pl_report.main() == 0
    output = capsys.readouterr().out
    position_line = next(line for line in output.splitlines() if "SMH" in line)
    assert "未計算" in position_line
