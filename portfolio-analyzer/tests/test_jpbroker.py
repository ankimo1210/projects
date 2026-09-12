"""Offline tests for the Japanese broker's trade-history CSV."""

from __future__ import annotations

from decimal import Decimal

from portfolio_analyzer import jpbroker

SAMPLE = """商品分類,約定日,受渡日,銘柄,取引,チャネル,約定単価,数量,受渡金額,備考
入金(配当),----/--/--,2026/08/14,8976 大和証券オフィス投資法人　投資証券,配当金,-,-,-,15260,NISA成長投資枠
上場投信,2026/03/09,2026/03/11,1329 ｉシェアーズ・コア　日経２２５　ＥＴＦ,買,オンライン,5360円,250,-1344548,NISA成長投資枠
入庫(増減資),----/--/--,2025/10/01,7532 パン・パシフィック,保振増減資,-,-,400,-,NISA成長投資枠
株式,2025/01/28,2025/01/30,7532 パン・パシフィック,買,オンライン,4219円,100,-423709,NISA成長投資枠
株式,2024/11/25,2024/11/27,9023 東京地下鉄,買,オンライン,1754円,300,-528424,特定
株式,2025/06/04,2025/06/06,9023 東京地下鉄,売,オンライン,1727円,300,515902,特定
入金(振込),----/--/--,2024/11/01,振込(振込専用口座),振込,-,-,-,600000,
"""


def test_decode_reads_the_broker_s_cp932_export() -> None:
    assert jpbroker.decode("商品分類,銘柄\n".encode("cp932")).startswith("商品分類")


def test_parse_splits_the_code_from_the_name() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    buy = next(r for r in rows if r.action == "買" and r.symbol == "1329")
    assert buy.name.startswith("ｉシェアーズ")
    assert buy.price == Decimal("5360")
    assert buy.quantity == Decimal("250")
    assert buy.amount == Decimal("-1344548")
    assert buy.trade_date == "2026-03-09"


def test_parse_keeps_cash_rows_without_a_stock_code() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    deposit = next(r for r in rows if r.kind.startswith("入金(振込)"))
    assert deposit.symbol is None and deposit.amount == Decimal("600000")


def test_derive_holdings_uses_the_settled_amount_as_the_cost() -> None:
    holdings = jpbroker.derive_holdings(jpbroker.parse_transactions(SAMPLE))
    h = holdings["1329"]
    assert h["quantity"] == Decimal("250")
    assert h["cost_basis_jpy"] == Decimal("1344548")  # the amount actually paid, fees included
    assert h["average_cost"] == Decimal("5360")
    assert h["commission_jpy"] == Decimal("-4548")  # 5360*250 = 1,340,000, paid 1,344,548
    assert h["average_trade_fx"] == Decimal("1")


def test_a_share_split_adds_quantity_without_adding_cost() -> None:
    h = jpbroker.derive_holdings(jpbroker.parse_transactions(SAMPLE))["7532"]
    assert h["quantity"] == Decimal("500")
    assert h["cost_basis_jpy"] == Decimal("423709")
    assert h["average_cost"] == Decimal("421900") / Decimal("500")  # execution price, split-adjusted


def test_a_closed_position_reports_its_realised_result_and_drops_out() -> None:
    holdings = jpbroker.derive_holdings(jpbroker.parse_transactions(SAMPLE))
    assert "9023" not in holdings
    closed = jpbroker.closed_positions(jpbroker.parse_transactions(SAMPLE))
    assert closed["9023"]["realized_pnl_jpy"] == Decimal("515902") - Decimal("528424")


def test_dividends_are_collected_per_symbol() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    assert jpbroker.dividends(rows)["8976"] == Decimal("15260")


def test_ledger_matches_the_shape_the_marker_expects() -> None:
    ledger = jpbroker.ledger(jpbroker.parse_transactions(SAMPLE), account_id="securities")
    assert ledger["account_id"] == "securities"
    entry = next(h for h in ledger["holdings"] if h["symbol"] == "1329")
    assert {"symbol", "quantity", "average_cost", "cost_basis_jpy", "commission_jpy"} <= set(entry)


def test_replay_walks_quantity_and_cost_through_the_dates() -> None:
    dates = ["2024-11-24", "2024-11-26", "2025-10-02", "2025-10-03"]
    paths = jpbroker.replay(jpbroker.parse_transactions(SAMPLE), dates)
    q = paths["7532"]["quantity"]
    cost = paths["7532"]["cost_basis_jpy"]
    # Yahoo's close is split-adjusted, so the quantity before the split is too
    assert q == [Decimal("0"), Decimal("0"), Decimal("500"), Decimal("500")]
    assert cost[0] == Decimal("0") and cost[2] == Decimal("423709")
    tokyo = paths["9023"]["quantity"]
    assert tokyo[1] == Decimal("300")  # bought 2024-11-25
    assert tokyo[-1] == Decimal("0")  # sold 2025-06-04
    # the marker sits on the adjusted price line: 100 shares at 4219 -> 500 at 843.8
    assert paths["7532"]["trades"] == [("2025-01-28", Decimal("500"), Decimal("843.8"))]


def test_replay_states_a_pre_split_holding_in_todays_shares() -> None:
    dates = ["2025-02-01", "2025-10-02"]
    paths = jpbroker.replay(jpbroker.parse_transactions(SAMPLE), dates)
    assert paths["7532"]["quantity"] == [Decimal("500"), Decimal("500")]
