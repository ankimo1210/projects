"""Offline tests for the daily mark-to-market P&L summary (no network)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from portfolio_analyzer import mtm

D = Decimal


def snapshot() -> dict:
    return {
        "snapshot_name": "test",
        "base_currency": "JPY",
        "accounts": [
            {
                "id": "dc",
                "name": "DC口座",
                "as_of": "2026-08-14",
                "total_value_jpy": 1000,
                "unrealized_pnl_jpy": 400,
                "daily_pnl_jpy": None,
            },
            {
                "id": "gb",
                "name": "海外証券口座",
                "as_of": "2026-08-15",
                "total_value_jpy": 6870000,
                "unrealized_pnl_jpy": None,
                "daily_pnl_jpy": None,
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
                "source_note": "残高",
            },
            {
                "account_id": "gb",
                "symbol": "1329",
                "name": "日経225 ETF",
                "asset_class": "日本株",
                "currency": "JPY",
                "quantity": 250,
                "price": 7096,
                "fx_rate": 1,
                "market_value_jpy": 1774000,
                "value_status": "exact",
                "source_note": "",
            },
            {
                "account_id": "gb",
                "symbol": "XLE",
                "name": "Energy",
                "asset_class": "米国株",
                "currency": "USD",
                "quantity": 500,
                "price": 61.9,
                "fx_rate": 159.4,
                "market_value_jpy": 4933293.18,
                "value_status": "estimated",
                "source_note": "",
            },
            {
                "account_id": "gb",
                "symbol": "CASH_JPY",
                "name": "円現金",
                "asset_class": "現金",
                "currency": "JPY",
                "quantity": None,
                "price": None,
                "fx_rate": 1,
                "market_value_jpy": 100000,
                "value_status": "exact",
                "source_note": "",
            },
        ],
    }


def quotes() -> dict[str, mtm.Quote]:
    return {
        "1329.T": mtm.Quote(
            close=D("7000"), prev_close=D("6900"), date="2026-09-11", prev_date="2026-09-10"
        ),
        "XLE": mtm.Quote(
            close=D("64"), prev_close=D("63"), date="2026-09-11", prev_date="2026-09-10"
        ),
    }


FX = mtm.Quote(close=D("160"), prev_close=D("159"), date="2026-09-11", prev_date="2026-09-10")


def ledger() -> dict:
    return {
        "account_id": "gb",
        "holdings": [
            {
                "symbol": "XLE",
                "currency": "USD",
                "quantity": 500.0,
                "average_cost": 53.865,
                "average_trade_fx": 161.6,
                "cost_basis_jpy": 4352696.2424,
                "commission_jpy": -404.2424,
            },
        ],
        "closed": [{"symbol": "LLY", "realized_pnl_jpy": -175786.23}],
    }


def test_mark_positions_values_and_day_pnl() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=None)
    by = {(r.account_id, r.symbol): r for r in rows}
    jp = by[("gb", "1329")]
    assert jp.quoted and jp.market_value_jpy == D("1750000")
    assert jp.day_pnl_jpy == D("25000")
    assert jp.day_change_pct == (D("7000") / D("6900") - 1)
    us = by[("gb", "XLE")]
    assert us.market_value_jpy == D("5120000")
    assert us.prev_value_jpy == D("500") * D("63") * D("159")
    assert us.day_pnl_jpy == us.market_value_jpy - us.prev_value_jpy
    assert us.day_price_pnl_jpy == D("500") * D("1") * D("160")
    cash = by[("gb", "CASH_JPY")]
    assert not cash.quoted and cash.market_value_jpy == D("100000") and cash.day_pnl_jpy is None
    assert by[("dc", "HAPPY_AGING_40")].market_value_jpy == D("1000")


def test_unrealized_pnl_from_ledger_cost_basis() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=ledger())
    by = {(r.account_id, r.symbol): r for r in rows}
    us = by[("gb", "XLE")]
    assert us.cost_basis_jpy == D("4352696.2424")
    assert us.unrealized_jpy == D("5120000") - D("4352696.2424")
    assert (
        us.price_pnl_jpy + us.fx_pnl_jpy + us.cross_pnl_jpy + us.commission_jpy == us.unrealized_jpy
    )
    assert us.price_pnl_jpy == (D("500") * D("64") - D("500") * D("53.865")) * D("161.6")
    assert by[("gb", "1329")].cost_basis_jpy is None and by[("gb", "1329")].unrealized_jpy is None


def test_summary_totals() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=ledger())
    s = mtm.summarize(snapshot(), rows)
    assert s.total_jpy == D("1000") + D("1750000") + D("5120000") + D("100000")
    assert s.day_pnl_jpy == D("25000") + (D("5120000") - D("500") * D("63") * D("159"))
    assert s.accounts["gb"].total_jpy == D("1750000") + D("5120000") + D("100000")
    assert s.accounts["gb"].day_pnl_jpy == s.day_pnl_jpy
    assert s.accounts["dc"].day_pnl_jpy is None
    assert s.unrealized_known_jpy == D("5120000") - D("4352696.2424")
    assert s.quoted_value_jpy == D("1750000") + D("5120000")


def test_history_upsert_replaces_same_date(tmp_path: Path) -> None:
    path = tmp_path / "hist.jsonl"
    mtm.upsert_history(path, {"as_of": "2026-09-10", "total_jpy": 100.0})
    mtm.upsert_history(path, {"as_of": "2026-09-11", "total_jpy": 110.0})
    records = mtm.upsert_history(path, {"as_of": "2026-09-11", "total_jpy": 111.0})
    assert [r["as_of"] for r in records] == ["2026-09-10", "2026-09-11"]
    assert records[-1]["total_jpy"] == 111.0
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2
    assert mtm.previous_record(records, "2026-09-11")["as_of"] == "2026-09-10"
    assert mtm.previous_record(records, "2026-09-10") is None


def test_render_html_carries_the_numbers() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=ledger())
    s = mtm.summarize(snapshot(), rows)
    html = mtm.render_html(
        s,
        rows,
        history=[],
        meta={
            "as_of": "2026-09-11",
            "generated_at": "2026-09-12T07:30:00+09:00",
            "fx": FX,
            "stale": {},
        },
        tokens_css=":root{--ink:#000}",
    )
    assert "2026-09-11" in html and "6,971,000" in html and "海外証券口座" in html
    assert "XLE" in html and "+25,000" in html
    assert "<!doctype" in html.lower() and "--ink" in html
    json.dumps(
        mtm.history_record(s, rows, meta={"as_of": "2026-09-11", "generated_at": "x", "fx": FX})
    )
