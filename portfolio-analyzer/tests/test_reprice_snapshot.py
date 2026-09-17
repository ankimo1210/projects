"""Offline tests for the snapshot repricing script (no network)."""

from __future__ import annotations

import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import pytest
from portfolio_analyzer.core import load_portfolio, validate_portfolio

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "reprice_snapshot", PROJECT_ROOT / "scripts/reprice_snapshot.py"
)
reprice_snapshot = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(reprice_snapshot)


@pytest.mark.parametrize(
    ("symbol", "currency", "expected"),
    [
        ("6857", "JPY", "6857.T"),
        ("1329", "JPY", "1329.T"),
        ("QQQ", "USD", "QQQ"),
        ("CASH_JPY", "JPY", None),
        ("RECONCILIATION", "JPY", None),
        ("HAPPY_AGING_40", "JPY", None),
    ],
)
def test_market_symbol(symbol: str, currency: str, expected: str | None) -> None:
    assert reprice_snapshot.market_symbol(symbol, currency) == expected


@pytest.fixture
def snapshot() -> dict:
    return {
        "snapshot_name": "before",
        "base_currency": "JPY",
        "accounts": [
            {
                "id": "dc",
                "name": "DC口座",
                "as_of": "2026-08-14",
                "total_value_jpy": 1000,
                "unrealized_pnl_jpy": 400,
                "daily_pnl_jpy": None,
                "quality_note": "残高のみ",
            },
            {
                "id": "broker",
                "name": "証券口座",
                "as_of": "2026-08-14",
                "total_value_jpy": 3000,
                "unrealized_pnl_jpy": 500,
                "daily_pnl_jpy": 10,
                "quality_note": "画面転記",
            },
        ],
        "positions": [
            {
                "account_id": "dc",
                "symbol": "HAPPY_AGING_40",
                "name": "バランス",
                "asset_class": "バランス型",
                "currency": "JPY",
                "quantity": None,
                "price": None,
                "fx_rate": 1,
                "market_value_jpy": 1000,
                "value_status": "exact",
                "source_note": "DC残高",
            },
            {
                "account_id": "broker",
                "symbol": "6857",
                "name": "アドバンテスト",
                "asset_class": "日本株",
                "currency": "JPY",
                "quantity": 200,
                "price": 36870,
                "fx_rate": 1,
                "market_value_jpy": 1000,
                "value_status": "exact",
                "source_note": "画面転記",
            },
            {
                "account_id": "broker",
                "symbol": "QQQ",
                "name": "QQQ",
                "asset_class": "米国株",
                "currency": "USD",
                "quantity": 10,
                "price": 730.85,
                "fx_rate": 159.39,
                "market_value_jpy": 1500,
                "value_status": "estimated",
                "source_note": "逆算",
                "fx_rate_status": "reconciliation_implied",
            },
            {
                "account_id": "broker",
                "symbol": "CASH_JPY",
                "name": "円現金",
                "asset_class": "現金",
                "currency": "JPY",
                "quantity": None,
                "price": None,
                "fx_rate": 1,
                "market_value_jpy": 500,
                "value_status": "exact",
                "source_note": "お預り金",
            },
        ],
    }


@pytest.fixture
def quotes() -> dict:
    return {
        "6857.T": {"close": Decimal("33690"), "date": "2026-08-31"},
        "QQQ": {"close": Decimal("721.11"), "date": "2026-08-27"},
    }


def test_reprice_recomputes_values_and_account_totals(snapshot: dict, quotes: dict) -> None:
    result = reprice_snapshot.reprice(snapshot, quotes, Decimal("159.794"), "2026-08-31")

    by_symbol = {row["symbol"]: row for row in result["positions"]}
    assert by_symbol["6857"]["market_value_jpy"] == pytest.approx(200 * 33690)
    assert by_symbol["QQQ"]["market_value_jpy"] == pytest.approx(10 * 721.11 * 159.794)
    assert by_symbol["QQQ"]["fx_rate"] == pytest.approx(159.794)

    broker = next(row for row in result["accounts"] if row["id"] == "broker")
    assert broker["total_value_jpy"] == pytest.approx(200 * 33690 + 10 * 721.11 * 159.794 + 500)


def test_reprice_writes_a_snapshot_that_validates(
    snapshot: dict, quotes: dict, tmp_path: Path
) -> None:
    result = reprice_snapshot.reprice(snapshot, quotes, Decimal("159.794"), "2026-08-31")
    path = tmp_path / "repriced.json"
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    assert validate_portfolio(load_portfolio(path)) == []


def test_repriced_positions_are_estimated_and_carry_their_price_date(
    snapshot: dict, quotes: dict
) -> None:
    result = reprice_snapshot.reprice(snapshot, quotes, Decimal("159.794"), "2026-08-31")

    by_symbol = {row["symbol"]: row for row in result["positions"]}
    assert by_symbol["6857"]["value_status"] == "estimated"
    assert by_symbol["6857"]["price_as_of"] == "2026-08-31"
    assert by_symbol["QQQ"]["price_as_of"] == "2026-08-27"
    # The implied FX rate was an artefact of the old reconciliation, not of this quote.
    assert "fx_rate_status" not in by_symbol["QQQ"]


def test_unquotable_positions_are_carried_forward(snapshot: dict, quotes: dict) -> None:
    result = reprice_snapshot.reprice(snapshot, quotes, Decimal("159.794"), "2026-08-31")

    by_symbol = {row["symbol"]: row for row in result["positions"]}
    assert by_symbol["HAPPY_AGING_40"]["market_value_jpy"] == 1000
    # A DC balance carried across two weeks is no longer a confirmed figure.
    assert by_symbol["HAPPY_AGING_40"]["value_status"] == "estimated"
    # Cash does not move with market prices, so the statement figure still holds.
    assert by_symbol["CASH_JPY"]["value_status"] == "exact"
    assert "据え置き" in by_symbol["CASH_JPY"]["source_note"]


def test_account_pnl_is_dropped_only_where_repricing_invalidated_it(
    snapshot: dict, quotes: dict
) -> None:
    result = reprice_snapshot.reprice(snapshot, quotes, Decimal("159.794"), "2026-08-31")

    accounts = {row["id"]: row for row in result["accounts"]}
    assert accounts["broker"]["unrealized_pnl_jpy"] is None
    assert accounts["broker"]["daily_pnl_jpy"] is None
    assert accounts["broker"]["as_of"] == "2026-08-31"
    # Nothing in the DC account was repriced, so its figures still describe it.
    assert accounts["dc"]["unrealized_pnl_jpy"] == 400
    assert accounts["dc"]["as_of"] == "2026-08-14"


def test_quotes_older_than_the_as_of_date_are_recorded(snapshot: dict, quotes: dict) -> None:
    result = reprice_snapshot.reprice(snapshot, quotes, Decimal("159.794"), "2026-08-31")

    assert result["repricing"]["quotes_older_than_as_of"] == {"QQQ": "2026-08-27"}


def test_reprice_does_not_mutate_the_input(snapshot: dict, quotes: dict) -> None:
    before = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)

    reprice_snapshot.reprice(snapshot, quotes, Decimal("159.794"), "2026-08-31")

    assert json.dumps(snapshot, ensure_ascii=False, sort_keys=True) == before


def test_last_final_close_skips_a_bar_still_trading() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import pandas as pd

    series = pd.Series([542.11, 550.22], index=pd.to_datetime(["2026-09-15", "2026-09-16"]))
    jst = ZoneInfo("Asia/Tokyo")
    live = reprice_snapshot.last_final_close(
        series, "SMH", datetime(2026, 9, 16, 23, 50, tzinfo=jst)
    )
    assert live == {"close": Decimal("542.1100"), "date": "2026-09-15"}
    done = reprice_snapshot.last_final_close(
        series, "SMH", datetime(2026, 9, 17, 7, 30, tzinfo=jst)
    )
    assert done == {"close": Decimal("550.2200"), "date": "2026-09-16"}


DC_HOLDING = {
    "account_id": "dc",
    "symbol": "HAPPY_AGING_40",
    "ticker": "SOMPO_AM:0885",
    "anchor": {"as_of": "2026-09-12", "units": 2901109, "contributions_jpy": 5184000},
}


def dc_trade(trade_date: str, units: str, amount: str):
    from portfolio_analyzer.dcplan import Trade

    return Trade(
        trade_date=trade_date,
        settle_date=trade_date,
        name="ハッピーエイジング４０",
        units=Decimal(units),
        price=Decimal("2.6"),
        amount=Decimal(amount),
        kind="買 掛金",
    )


def test_fund_quote_values_the_plan_units_at_the_last_price_on_or_before_the_day() -> None:
    nav = [("2026-09-15", Decimal("25885")), ("2026-09-16", Decimal("25964"))]
    trades = [dc_trade("2026-09-28", "21000", "55000")]  # after the day: not held yet
    quote = reprice_snapshot.fund_quote(DC_HOLDING, trades, nav, "2026-09-16")
    assert quote == {
        "ticker": "SOMPO_AM:0885",
        "quantity": Decimal("290.1109"),
        "close": Decimal("25964"),
        "date": "2026-09-16",
        "cost_basis_jpy": Decimal("5184000"),
    }
    later = reprice_snapshot.fund_quote(DC_HOLDING, trades, nav, "2026-09-30")
    assert later is not None and later["quantity"] == Decimal("292.2109")
    assert later["cost_basis_jpy"] == Decimal("5239000") and later["date"] == "2026-09-16"
    assert reprice_snapshot.fund_quote(DC_HOLDING, trades, nav, "2026-09-14") is None


def test_the_dc_fund_is_repriced_with_its_account_pnl(
    snapshot: dict, quotes: dict, tmp_path: Path
) -> None:
    fund = {
        "ticker": "SOMPO_AM:0885",
        "quantity": Decimal("290.1109"),
        "close": Decimal("25964"),
        "date": "2026-08-31",
        "cost_basis_jpy": Decimal("5184000"),
    }
    result = reprice_snapshot.reprice(
        snapshot, quotes, Decimal("159.794"), "2026-08-31", funds={("dc", "HAPPY_AGING_40"): fund}
    )
    dc_pos = next(r for r in result["positions"] if r["symbol"] == "HAPPY_AGING_40")
    value = float((Decimal("290.1109") * Decimal("25964")).quantize(Decimal("0.01")))
    assert dc_pos["quantity"] == pytest.approx(290.1109)
    assert dc_pos["price"] == 25964
    assert dc_pos["market_value_jpy"] == pytest.approx(value)
    assert dc_pos["value_status"] == "estimated" and dc_pos["price_as_of"] == "2026-08-31"
    assert "基準価額" in dc_pos["source_note"]

    dc = next(a for a in result["accounts"] if a["id"] == "dc")
    assert dc["as_of"] == "2026-08-31"
    assert dc["total_value_jpy"] == pytest.approx(value)
    assert dc["unrealized_pnl_jpy"] == pytest.approx(value - 5184000)
    assert result["repricing"]["quotes"]["SOMPO_AM:0885"] == "2026-08-31"

    path = tmp_path / "repriced.json"
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    assert validate_portfolio(load_portfolio(path)) == []
