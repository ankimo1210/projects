"""Offline tests for the Japanese broker's trade-history CSV."""

from __future__ import annotations

from decimal import Decimal

from portfolio_analyzer import jpbroker
from portfolio_analyzer import timeseries as ts

D = Decimal

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


def test_holdings_carry_the_tax_category_of_the_lots_still_held() -> None:
    holdings = jpbroker.derive_holdings(jpbroker.parse_transactions(SAMPLE))
    assert holdings["1329"]["tax_category"] == "nisa"
    assert holdings["7532"]["tax_category"] == "nisa"


def test_a_symbol_bought_in_both_nisa_and_a_taxable_account_is_mixed() -> None:
    extra = "株式,2026/04/01,2026/04/03,1329 ｉシェアーズ・コア　日経２２５　ＥＴＦ,買,オンライン,5400円,10,-54100,特定\n"
    h = jpbroker.derive_holdings(jpbroker.parse_transactions(SAMPLE + extra))["1329"]
    assert h["tax_category"] == "mixed"


def test_a_taxable_lot_sold_out_before_a_nisa_rebuy_does_not_count() -> None:
    rebuy = "株式,2025/07/01,2025/07/03,9023 東京地下鉄,買,オンライン,1600円,100,-160500,NISA成長投資枠\n"
    h = jpbroker.derive_holdings(jpbroker.parse_transactions(SAMPLE + rebuy))["9023"]
    assert h["quantity"] == Decimal("100") and h["tax_category"] == "nisa"


def test_a_share_split_adds_quantity_without_adding_cost() -> None:
    h = jpbroker.derive_holdings(jpbroker.parse_transactions(SAMPLE))["7532"]
    assert h["quantity"] == Decimal("500")
    assert h["cost_basis_jpy"] == Decimal("423709")
    assert h["average_cost"] == Decimal("421900") / Decimal(
        "500"
    )  # execution price, split-adjusted


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


def test_taxable_realized_since_skips_nisa_sales_and_earlier_years() -> None:
    nisa_sale = "株式,2025/08/01,2025/08/05,7532 パン・パシフィック,売,オンライン,5000円,100,499000,NISA成長投資枠\n"
    rows = jpbroker.parse_transactions(SAMPLE + nisa_sale)
    assert jpbroker.taxable_realized_since(rows, "2025-01-01") == Decimal("515902") - Decimal(
        "528424"
    )
    assert jpbroker.taxable_realized_since(rows, "2026-01-01") == Decimal("0")


DATES = [
    "2024-11-01",
    "2024-11-25",
    "2025-01-28",
    "2025-06-04",
    "2025-10-01",
    "2026-03-09",
    "2026-08-14",
]


def _prices():
    # 9023 until it is sold, 7532 (post-split shares), 1329
    return {
        "9023": [None, D("1754"), D("1800"), D("1727"), D("1727"), D("1727"), D("1727")],
        "7532": [None, None, D("4219"), D("4000"), D("1000"), D("900"), D("726")],
        "1329": [None, None, None, None, None, D("5360"), D("6636")],
        "8976": [None] * 7,
    }


def test_account_paths_replays_cash_from_the_settled_amounts() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    s = jpbroker.account_paths(rows, DATES, _prices())
    assert s.account_id == "securities"
    # deposit only
    assert s.nav[0] == D(600000) and s.deposits_cum[0] == D(600000) and s.pnl[0] == D(0)
    # after buying 9023: cash 600000 − 528424, position 300 × 1754
    assert s.nav[1] == D(600000) - D(528424) + D(300) * D(1754)
    # the sale realises 515902 − 528424 and the dividend later lands in cash
    assert s.realized_cum[3] == D(515902) - D(528424)
    assert s.dividends_cum[-1] == D(15260) and s.dividends_cum[3] == D(0)


def test_account_paths_keeps_the_bucket_identity_on_every_date() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    s = jpbroker.account_paths(rows, DATES, _prices())
    for i, date in enumerate(DATES):
        if s.nav[i] is None:
            continue
        parts = sum((getattr(s, b)[i] for b in ts.BUCKETS), D(0))
        assert parts == s.pnl[i], date
    assert s.fees_cum == [D(0)] * len(DATES)  # commissions sit inside the cost basis


def test_account_paths_is_undefined_while_a_held_symbol_has_no_price() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    prices = _prices()
    prices["1329"][-1] = None
    s = jpbroker.account_paths(rows, DATES, prices)
    assert s.nav[-1] is None and s.pnl[-1] is None and s.unrealized[-1] is None
    assert s.deposits_cum[-1] == D(600000)  # cash-side paths never depend on a price


def test_replay_carries_realised_pnl_per_symbol() -> None:
    rows = jpbroker.parse_transactions(SAMPLE)
    path = jpbroker.replay(rows, DATES)["9023"]
    assert path["realized_cum"][2] == D(0) and path["realized_cum"][3] == D(515902) - D(528424)
