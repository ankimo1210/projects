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
    assert us.day_stock_pnl_jpy == D("500") * D("1") * D("160")
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


def test_day_pnl_splits_into_stock_and_fx() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=None)
    by = {(r.account_id, r.symbol): r for r in rows}
    us = by[("gb", "XLE")]
    assert us.day_stock_pnl_jpy == D("500") * (D("64") - D("63")) * D("160")
    assert us.day_fx_pnl_jpy == D("500") * D("63") * (D("160") - D("159"))
    assert us.day_stock_pnl_jpy + us.day_fx_pnl_jpy == us.day_pnl_jpy
    jp = by[("gb", "1329")]
    assert jp.day_stock_pnl_jpy == jp.day_pnl_jpy and jp.day_fx_pnl_jpy == D("0")
    cash = by[("gb", "CASH_JPY")]
    assert cash.day_stock_pnl_jpy is None and cash.day_fx_pnl_jpy is None


def test_unrealized_pnl_splits_into_stock_and_fx() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=ledger())
    us = {(r.account_id, r.symbol): r for r in rows}[("gb", "XLE")]
    assert us.unrealized_fx_jpy == us.fx_pnl_jpy
    assert us.unrealized_fx_jpy == D("500") * D("53.865") * D("160") - (
        D("4352696.2424") - D("404.2424")
    )
    assert us.unrealized_stock_jpy + us.unrealized_fx_jpy == us.unrealized_jpy


def test_unrealized_fx_is_zero_for_yen_holdings() -> None:
    # A yen ledger whose cost basis carries commission: the raw decomposition's FX term
    # would pick that up, but a yen holding has no currency exposure.
    yen_ledger = {
        "account_id": "gb",
        "holdings": [
            {
                "symbol": "1329",
                "currency": "JPY",
                "quantity": 250,
                "average_cost": 6000,
                "average_trade_fx": 1,
                "cost_basis_jpy": 1500500,
                "commission_jpy": 500,
            }
        ],
    }
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=yen_ledger)
    jp = {(r.account_id, r.symbol): r for r in rows}[("gb", "1329")]
    assert jp.unrealized_fx_jpy == D("0")
    assert jp.unrealized_stock_jpy == jp.unrealized_jpy


def test_summary_carries_the_stock_fx_split() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=ledger())
    s = mtm.summarize(snapshot(), rows)
    assert s.day_stock_pnl_jpy + s.day_fx_pnl_jpy == s.day_pnl_jpy
    assert s.day_fx_pnl_jpy == D("500") * D("63") * D("1")
    assert s.unrealized_stock_jpy + s.unrealized_fx_jpy == s.unrealized_known_jpy
    gb = s.accounts["gb"]
    assert gb.day_stock_pnl_jpy + gb.day_fx_pnl_jpy == gb.day_pnl_jpy
    assert gb.unrealized_stock_jpy + gb.unrealized_fx_jpy == gb.unrealized_known_jpy
    assert s.accounts["dc"].day_fx_pnl_jpy is None


def test_mark_positions_uses_a_position_s_own_ticker_when_it_names_one() -> None:
    snap = snapshot()
    dc = snap["positions"][0]
    dc.update(ticker="SOMPO_AM:0885", quantity=D("290.1109"))
    q = quotes() | {
        "SOMPO_AM:0885": mtm.Quote(
            close=D("25885"), prev_close=D("25962"), date="2026-09-11", prev_date="2026-09-10"
        )
    }
    rows = mtm.mark_positions(snap, q, FX, ledger=None)
    row = {(r.account_id, r.symbol): r for r in rows}[("dc", "HAPPY_AGING_40")]
    assert row.quoted and row.ticker == "SOMPO_AM:0885"
    assert row.market_value_jpy == D("290.1109") * D("25885")
    assert row.day_fx_pnl_jpy == D("0")


def _taxed_snapshot() -> dict:
    snap = snapshot()
    rates = {"dc": 0, "gb": 0.20315}
    for acc in snap["accounts"]:
        acc["tax_rate"] = rates[acc["id"]]
    return snap


RATE = D("0.20315")
U_XLE = D("5120000") - D("4352696.2424")  # XLE gain in gb
DAY_XLE = D("5120000") - D("500") * D("63") * D("159")


def _netting_case(category: str | None = None) -> tuple[dict, list[dict]]:
    """XLE (a gain) in the foreign account, 1329 (a -250,000 loss) in a second, domestic one."""
    snap = _taxed_snapshot()
    snap["accounts"].append(
        {"id": "jp", "name": "国内証券口座", "as_of": "2026-08-15", "tax_rate": 0.20315}
    )
    snap["positions"][1]["account_id"] = "jp"
    domestic = {
        "account_id": "jp",
        "holdings": [
            {
                "symbol": "1329",
                "currency": "JPY",
                "quantity": 250,
                "average_cost": 8000,
                "average_trade_fx": 1,
                "cost_basis_jpy": 2000000,
                "commission_jpy": 0,
                **({"tax_category": category} if category else {}),
            }
        ],
    }
    return snap, [ledger(), domestic]


def _marked(snap: dict, ledgers: list[dict], **tax) -> tuple[list[mtm.Row], mtm.TaxPool]:
    rows = mtm.mark_positions(snap, quotes(), FX, ledger=ledgers)
    return rows, mtm.net_tax(rows, **tax)


def test_rates_come_from_the_account_a_nisa_holding_or_the_position() -> None:
    snap = _taxed_snapshot()
    snap["positions"][2]["tax_rate"] = 0  # XLE held somewhere tax-free
    rows = mtm.mark_positions(snap, quotes(), FX, ledger=ledger())
    by = {(r.account_id, r.symbol): r for r in rows}
    assert by[("gb", "XLE")].tax_rate == D("0")
    assert by[("gb", "1329")].tax_rate == RATE
    snap, ledgers = _netting_case("nisa")
    rows = mtm.mark_positions(snap, quotes(), FX, ledger=ledgers)
    assert {(r.account_id, r.symbol): r for r in rows}[("jp", "1329")].tax_rate == D("0")


def test_a_mixed_holding_takes_the_account_s_taxable_rate() -> None:
    snap, ledgers = _netting_case("mixed")
    rows = mtm.mark_positions(snap, quotes(), FX, ledger=ledgers)
    jp = {(r.account_id, r.symbol): r for r in rows}[("jp", "1329")]
    assert jp.tax_rate == RATE and jp.tax_category == "mixed"


def test_a_loss_in_one_account_offsets_a_gain_in_another() -> None:
    rows, pool = _marked(*_netting_case())
    by = {(r.account_id, r.symbol): r for r in rows}
    net = U_XLE - D("250000")
    assert pool.unrealized_jpy == net and pool.rate == RATE
    assert pool.tax_jpy == net * RATE
    xle, jp = by[("gb", "XLE")], by[("jp", "1329")]
    # the whole tax sits on the position with the gain; the loss position pays none
    assert xle.unrealized_tax_jpy == pool.tax_jpy
    assert xle.unrealized_after_tax_jpy == U_XLE - pool.tax_jpy
    assert jp.unrealized_tax_jpy == D("0") and jp.unrealized_after_tax_jpy == D("-250000")


def test_daily_after_tax_takes_off_the_change_in_the_estimated_tax() -> None:
    rows, pool = _marked(*_netting_case())
    by = {(r.account_id, r.symbol): r for r in rows}
    prev_net = (U_XLE - DAY_XLE) + (D("-250000") - D("25000"))
    assert pool.prev_tax_jpy == prev_net * RATE
    change = pool.tax_jpy - pool.prev_tax_jpy
    assert by[("gb", "XLE")].day_pnl_after_tax_jpy == DAY_XLE - change
    assert by[("jp", "1329")].day_pnl_after_tax_jpy == D("25000")


def test_nisa_holdings_stay_out_of_the_netting() -> None:
    rows, pool = _marked(*_netting_case("nisa"))
    jp = {(r.account_id, r.symbol): r for r in rows}[("jp", "1329")]
    assert pool.unrealized_jpy == U_XLE and pool.tax_jpy == U_XLE * RATE
    assert jp.unrealized_after_tax_jpy == jp.unrealized_jpy
    assert jp.day_pnl_after_tax_jpy == jp.day_pnl_jpy


def test_a_net_loss_owes_no_tax() -> None:
    snap, ledgers = _netting_case()
    ledgers[1]["holdings"][0]["cost_basis_jpy"] = 3000000  # 1329 now -1,250,000
    rows, pool = _marked(snap, ledgers)
    assert pool.tax_jpy == D("0")
    for r in rows:
        if r.unrealized_jpy is not None:
            assert r.unrealized_after_tax_jpy == r.unrealized_jpy


def test_a_carried_forward_loss_shrinks_the_taxable_gain() -> None:
    _, pool = _marked(*_netting_case(), carryforward_loss_jpy=D("500000"))
    assert pool.tax_jpy == (U_XLE - D("250000") - D("500000")) * RATE


def test_selling_at_a_loss_would_win_back_tax_on_gains_already_realised_this_year() -> None:
    snap, ledgers = _netting_case()
    snap["positions"][2]["tax_rate"] = 0  # only the 1329 loss is taxable
    rows, pool = _marked(snap, ledgers, realized_ytd_jpy=D("300000"))
    jp = {(r.account_id, r.symbol): r for r in rows}[("jp", "1329")]
    # (-250,000 + 300,000) x rate owed in all, 300,000 x rate owed without selling
    assert pool.tax_jpy == (D("50000") - D("300000")) * RATE
    assert jp.unrealized_tax_jpy == pool.tax_jpy
    assert jp.unrealized_after_tax_jpy == D("-250000") * (1 - RATE)


def test_positions_taxed_at_different_rates_cannot_be_netted() -> None:
    snap, ledgers = _netting_case()
    snap["positions"][2]["tax_rate"] = 0.1
    rows = mtm.mark_positions(snap, quotes(), FX, ledger=ledgers)
    try:
        mtm.net_tax(rows)
    except ValueError as exc:
        assert "rate" in str(exc)
    else:
        raise AssertionError("expected a ValueError")


def test_summary_nets_tax_out_of_the_totals() -> None:
    snap, ledgers = _netting_case()
    rows, pool = _marked(snap, ledgers)
    s = mtm.summarize(snap, rows)
    assert s.unrealized_tax_jpy == pool.tax_jpy
    assert s.total_after_tax_jpy == s.total_jpy - pool.tax_jpy
    assert s.unrealized_after_tax_jpy == s.unrealized_known_jpy - pool.tax_jpy
    assert s.day_pnl_after_tax_jpy == s.day_pnl_jpy - (pool.tax_jpy - pool.prev_tax_jpy)
    assert s.accounts["gb"].total_after_tax_jpy == s.accounts["gb"].total_jpy - pool.tax_jpy
    assert s.accounts["jp"].total_after_tax_jpy == s.accounts["jp"].total_jpy
    assert s.accounts["dc"].total_after_tax_jpy == s.accounts["dc"].total_jpy


def test_after_tax_is_unknown_when_a_position_with_pnl_has_no_rate() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=ledger())
    mtm.net_tax(rows)
    s = mtm.summarize(snapshot(), rows)
    assert s.day_pnl_after_tax_jpy is None and s.total_after_tax_jpy is None


def test_a_taxable_position_without_a_cost_leaves_after_tax_unknown() -> None:
    rows, _ = _marked(_taxed_snapshot(), [ledger()])  # 1329 in gb has no cost
    jp = {(r.account_id, r.symbol): r for r in rows}[("gb", "1329")]
    assert jp.day_pnl_after_tax_jpy is None


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


def test_history_record_is_json_serialisable() -> None:
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=ledger())
    s = mtm.summarize(snapshot(), rows)
    rec = mtm.history_record(s, rows, meta={"as_of": "2026-09-11", "generated_at": "x", "fx": FX})
    back = json.loads(json.dumps(rec))
    assert back["total_jpy"] == 6971000.0
    assert back["day_stock_pnl_jpy"] + back["day_fx_pnl_jpy"] == back["day_pnl_jpy"]
    assert back["positions"]["gb:XLE"]["day_fx_pnl_jpy"] == 31500.0


def test_mark_positions_accepts_one_ledger_per_account() -> None:
    # The domestic account keeps its own history, so the marker takes several ledgers.
    domestic = {
        "account_id": "gb",
        "holdings": [
            {
                "symbol": "1329",
                "currency": "JPY",
                "quantity": 250.0,
                "average_cost": 6800.0,
                "average_trade_fx": 1.0,
                "cost_basis_jpy": 1700500.0,
                "commission_jpy": -500.0,
            }
        ],
    }
    rows = mtm.mark_positions(snapshot(), quotes(), FX, ledger=[ledger(), domestic])
    by = {(r.account_id, r.symbol): r for r in rows}
    assert by[("gb", "XLE")].unrealized_jpy is not None
    jp = by[("gb", "1329")]
    assert jp.cost_basis_jpy == D("1700500")
    assert jp.unrealized_jpy == D("1750000") - D("1700500")


def test_tax_note_states_each_account_s_rates_and_the_loss_assumption() -> None:
    snap = _taxed_snapshot()
    snap["accounts"][0]["tax_note"] = "受取時の控除内とみなす"
    nisa = {
        "account_id": "gb",
        "holdings": [
            {
                "symbol": "1329",
                "currency": "JPY",
                "quantity": 250,
                "average_cost": 6000,
                "average_trade_fx": 1,
                "cost_basis_jpy": 1500000,
                "commission_jpy": 0,
                "tax_category": "nisa",
            }
        ],
    }
    snap["positions"][0].update(ticker="SOMPO_AM:0885", quantity=D("290.1109"))
    q = quotes() | {
        "SOMPO_AM:0885": mtm.Quote(
            close=D("25885"), prev_close=D("25962"), date="2026-09-11", prev_date="2026-09-10"
        )
    }
    rows = mtm.mark_positions(snap, q, FX, ledger=[ledger(), nisa])
    pool = mtm.net_tax(rows, realized_ytd_jpy=D("12345"), carryforward_loss_jpy=D("0"))
    note = mtm.tax_note(snap, rows, pool)
    assert "海外証券口座 NISA 0%・その他 20.315%" in note
    assert "DC口座 0%（受取時の控除内とみなす）" in note
    assert "損益通算" in note and "今年の実現損益 +12,345" in note and "繰越損失 0" in note
    assert f"見込み税額 {round(pool.tax_jpy):,} 円" in note


def test_tax_note_ignores_positions_without_pnl() -> None:
    snap = _taxed_snapshot()
    snap["positions"] = [p for p in snap["positions"] if p["symbol"] in ("1329", "CASH_JPY")]
    nisa = {
        "account_id": "gb",
        "holdings": [
            {
                "symbol": "1329",
                "currency": "JPY",
                "quantity": 250,
                "average_cost": 6000,
                "average_trade_fx": 1,
                "cost_basis_jpy": 1500000,
                "commission_jpy": 0,
                "tax_category": "nisa",
            }
        ],
    }
    rows = mtm.mark_positions(snap, quotes(), FX, ledger=nisa)
    assert "海外証券口座 NISA 0%。" in mtm.tax_note(snap, rows, mtm.net_tax(rows))
