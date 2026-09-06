"""Tests for the IBKR transaction-history reader (synthetic rows only, no private data)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from portfolio_analyzer import ibkr

HEADER = (
    "Statement,Header,フィールド名,フィールド価値\n"
    "Statement,Data,Title,Transaction History\n"
    "Summary,Header,フィールド名,フィールド価値\n"
    "Summary,Data,基準通貨,JPY\n"
    "Transaction History,Header,Date,Account,Description,Transaction Type,Symbol,"
    "Quantity,価格,Price Currency,Gross Amount ,Commission,Net Amount\n"
)


def statement(*rows: str) -> str:
    return HEADER + "".join(f"Transaction History,Data,{row}\n" for row in rows)


BUY_QQQ = (
    "2026-08-05,U***69554,INVESCO QQQ TRUST SERIES 1,Buy,QQQ,10.0,727.715,USD,"
    "-1148115.9555,-157.77473310000002,-1148273.7302331"
)
BUY_TOPIX = (
    "2026-08-05,U***69554,ISHARES CORE TOPIX ETF,Buy,1475.T,2500.0,417.2,JPY,"
    "-1043000.0,-834.0,-1043834.0"
)
DEPOSIT = "2026-08-06,U***69554,電信扱い,Deposit,-,-,-,-,5000000.0,-,5000000.0"


def test_parse_transactions_reads_only_the_transaction_history_section() -> None:
    ledger = ibkr.parse_transactions(statement(BUY_QQQ, DEPOSIT))

    assert [row.transaction_type for row in ledger] == ["Buy", "Deposit"]


def test_parse_transactions_keeps_amounts_as_exact_decimals() -> None:
    (buy,) = ibkr.parse_transactions(statement(BUY_QQQ))

    assert buy.symbol == "QQQ"
    assert buy.quantity == Decimal("10.0")
    assert buy.price == Decimal("727.715")
    assert buy.price_currency == "USD"
    assert buy.gross_amount == Decimal("-1148115.9555")
    assert buy.commission == Decimal("-157.77473310000002")
    assert buy.net_amount == Decimal("-1148273.7302331")


def test_parse_transactions_maps_the_dash_placeholder_to_none() -> None:
    (deposit,) = ibkr.parse_transactions(statement(DEPOSIT))

    assert deposit.symbol is None
    assert deposit.quantity is None
    assert deposit.price is None
    assert deposit.price_currency is None
    assert deposit.commission is None
    assert deposit.net_amount == Decimal("5000000.0")


def test_parse_transactions_rejects_an_unexpected_column_layout() -> None:
    broken = HEADER.replace("Net Amount", "Total Amount")

    with pytest.raises(ValueError, match="column"):
        ibkr.parse_transactions(broken)


SELL_QQQ_ALL = (
    "2026-08-20,U***69554,INVESCO QQQ TRUST SERIES 1,Sell,QQQ,-10.0,800.0,USD,"
    "1280000.0,-160.0,1279840.0"
)
SELL_QQQ_HALF = (
    "2026-08-20,U***69554,INVESCO QQQ TRUST SERIES 1,Sell,QQQ,-5.0,800.0,USD,"
    "640000.0,-80.0,639920.0"
)


def test_derive_holdings_accumulates_quantity_and_jpy_cost_including_commission() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(BUY_TOPIX, BUY_TOPIX)))

    topix = holdings["1475.T"]
    assert topix.quantity == Decimal("5000.0")
    assert topix.cost_basis_jpy == Decimal("2087668.0")
    assert topix.currency == "JPY"
    assert topix.average_trade_fx == Decimal("1")


def test_derive_holdings_recovers_the_trade_date_fx_rate_from_gross_over_native() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(BUY_QQQ)))

    qqq = holdings["QQQ"]
    assert qqq.currency == "USD"
    assert qqq.cost_basis_native == Decimal("7277.150")
    assert qqq.average_trade_fx == Decimal("157.77")


def test_derive_holdings_reports_realized_pnl_when_a_position_is_closed() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(BUY_QQQ, SELL_QQQ_ALL)))

    qqq = holdings["QQQ"]
    assert qqq.quantity == Decimal("0")
    assert qqq.cost_basis_jpy == Decimal("0")
    assert qqq.cost_basis_native == Decimal("0")
    assert qqq.realized_pnl_jpy == Decimal("1279840.0") - Decimal("1148273.7302331")
    assert qqq.is_closed


def test_derive_holdings_removes_average_cost_in_proportion_to_a_partial_sell() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(BUY_QQQ, SELL_QQQ_HALF)))

    qqq = holdings["QQQ"]
    assert qqq.quantity == Decimal("5.0")
    assert qqq.cost_basis_jpy == Decimal("1148273.7302331") / 2
    assert qqq.cost_basis_native == Decimal("7277.150") / 2
    assert qqq.realized_pnl_jpy == Decimal("639920.0") - Decimal("1148273.7302331") / 2
    assert not qqq.is_closed


def test_derive_holdings_ignores_rows_that_are_not_trades() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(DEPOSIT, BUY_QQQ)))

    assert list(holdings) == ["QQQ"]


def test_derive_holdings_rejects_a_sell_of_more_than_is_held() -> None:
    transactions = ibkr.parse_transactions(statement(SELL_QQQ_ALL))

    with pytest.raises(ValueError, match="QQQ"):
        ibkr.derive_holdings(transactions)


DIVIDEND = (
    "2026-08-20,U***69554,2561.T 現金配当 JPY 6 一株当たり： (通常配当),Dividend,2561.T,"
    "-,-,-,9000.0,-,9000.0"
)
WITHHOLDING = (
    "2026-08-20,U***69554,2561.T 現金配当 JPY 6 一株当たり： - JP NATIONAL Tax,"
    "Foreign Tax Withholding,2561.T,-,-,-,-1378.0,-,-1378.0"
)
OTHER_FEE = "2026-08-06,U***69554,消費税（手数料、課税額： 834),Other Fee,-,-,-,-,-83.0,-,-83.0"
FX_TRANSLATION = (
    "2026-09-04,U***69554,FX Translations P&L,Adjustment,-,-,-,-,"
    "1077795.973919265,-,1077795.973919265"
)
EARLIER_DEPOSIT = "2026-07-07,U***69554,電信扱い,Deposit,-,-,-,-,3000000.0,-,3000000.0"


def test_summarize_cash_totals_every_net_amount_into_the_ending_balance() -> None:
    text = statement(FX_TRANSLATION, DIVIDEND, WITHHOLDING, OTHER_FEE, DEPOSIT, BUY_QQQ)

    summary = ibkr.summarize_cash(ibkr.parse_transactions(text))

    assert summary.ending_cash_jpy == (
        Decimal("1077795.973919265")
        + Decimal("9000.0")
        - Decimal("1378.0")
        - Decimal("83.0")
        + Decimal("5000000.0")
        - Decimal("1148273.7302331")
    )


def test_summarize_cash_separates_the_income_and_cost_buckets() -> None:
    text = statement(FX_TRANSLATION, DIVIDEND, WITHHOLDING, OTHER_FEE, DEPOSIT, BUY_QQQ)

    summary = ibkr.summarize_cash(ibkr.parse_transactions(text))

    assert summary.deposits_jpy == Decimal("5000000.0")
    assert summary.dividends_jpy == Decimal("9000.0")
    assert summary.withholding_tax_jpy == Decimal("-1378.0")
    assert summary.other_fees_jpy == Decimal("-83.0")
    assert summary.trade_commissions_jpy == Decimal("-157.77473310000002")
    assert summary.fx_translation_pnl_jpy == Decimal("1077795.973919265")


def test_summarize_cash_lists_deposits_oldest_first() -> None:
    summary = ibkr.summarize_cash(ibkr.parse_transactions(statement(DEPOSIT, EARLIER_DEPOSIT)))

    assert summary.deposit_flows == [
        ("2026-07-07", Decimal("3000000.0")),
        ("2026-08-06", Decimal("5000000.0")),
    ]


def test_money_weighted_return_recovers_a_flat_ten_percent_year() -> None:
    flows = [("2024-01-01", Decimal("-100")), ("2024-12-31", Decimal("110"))]

    rate = ibkr.money_weighted_return(flows)

    assert rate is not None
    assert abs(rate - Decimal("0.10")) < Decimal("1e-9")


def test_money_weighted_return_handles_a_contribution_midway() -> None:
    flows = [
        ("2024-01-01", Decimal("-100")),
        ("2024-12-31", Decimal("-100")),
        ("2025-12-31", Decimal("231")),
    ]

    rate = ibkr.money_weighted_return(flows)

    assert rate is not None
    assert abs(rate - Decimal("0.10")) < Decimal("1e-9")


def test_money_weighted_return_is_undefined_when_no_sign_change_exists() -> None:
    flows = [("2024-01-01", Decimal("-100")), ("2024-12-31", Decimal("-100"))]

    assert ibkr.money_weighted_return(flows) is None


def test_decompose_pnl_splits_a_foreign_holding_into_price_fx_and_cross_terms() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(BUY_QQQ)))

    split = ibkr.decompose_pnl(holdings["QQQ"], Decimal("716.76"), Decimal("159.915"))

    assert split.market_value_jpy == Decimal("10") * Decimal("716.76") * Decimal("159.915")
    assert split.price_jpy < 0  # 727.715 -> 716.76
    assert split.fx_jpy > 0  # 157.77 -> 159.915
    # Derived from gross - net, not read off the Commission column: the export rounds that
    # column through a float, and only the derived figure keeps the four terms exact.
    assert abs(split.commission_jpy + Decimal("157.77473310000002")) < Decimal("1e-9")


def test_decompose_pnl_terms_add_back_to_the_total() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(BUY_QQQ)))

    split = ibkr.decompose_pnl(holdings["QQQ"], Decimal("716.76"), Decimal("159.915"))

    assert split.price_jpy + split.fx_jpy + split.cross_jpy + split.commission_jpy == (
        split.total_jpy
    )
    assert split.total_jpy == split.market_value_jpy - Decimal("1148273.7302331")


def test_decompose_pnl_leaves_no_fx_term_for_a_yen_holding() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(BUY_TOPIX)))

    split = ibkr.decompose_pnl(holdings["1475.T"], Decimal("430.5"), Decimal("1"))

    assert split.fx_jpy == 0
    assert split.cross_jpy == 0
    assert split.price_jpy == Decimal("2500") * (Decimal("430.5") - Decimal("417.2"))


def test_decompose_pnl_reports_nothing_for_a_closed_position() -> None:
    holdings = ibkr.derive_holdings(ibkr.parse_transactions(statement(BUY_QQQ, SELL_QQQ_ALL)))

    assert ibkr.decompose_pnl(holdings["QQQ"], Decimal("716.76"), Decimal("159.915")) is None


FOREX_COMPONENT = (
    "2026-08-06,U***69554,為替取引によるベース合計金額: 1 USD.JPY,Forex Trade Component,USD.JPY,"
    "1.0,157.809,JPY,0.6510000000000105,-,0.6510000000000105"
)


def test_summarize_cash_buckets_the_realised_fx_on_currency_conversions() -> None:
    summary = ibkr.summarize_cash(ibkr.parse_transactions(statement(FOREX_COMPONENT, DEPOSIT)))

    assert summary.forex_trade_component_jpy == Decimal("0.6510000000000105")
    assert summary.deposits_jpy == Decimal("5000000.0")
