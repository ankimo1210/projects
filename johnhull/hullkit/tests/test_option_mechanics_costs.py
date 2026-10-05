"""Hull §10.6: bid/ask costs, commissions and independent execution cash ledgers."""

import importlib
from decimal import Decimal

import pytest


def model():
    return importlib.import_module("hullkit._option_mechanics")


def test_printed_midpoint_hidden_cost_and_contract_units():
    row = model().option_trade_costs(4, 4.5)
    assert row["midpoint"] == pytest.approx(4.25)
    assert row["half_spread"] == pytest.approx(0.25)
    assert row["cost_per_contract"] == pytest.approx(25)


@pytest.mark.parametrize("contracts", [1, 3, 10])
def test_order_cashflows_against_independent_decimal_fill_accounting(contracts):
    row = model().option_trade_costs(4, 4.5, contracts=contracts, fixed_fee=2.5, fee_per_contract=0.5)
    fee = Decimal("2.5") + contracts * Decimal("0.5")
    buys = sum(Decimal("4.5") * 100 for _ in range(contracts))
    sells = sum(Decimal("4") * 100 for _ in range(contracts))
    middle = (buys + sells) / 2
    assert row["commission"] == pytest.approx(float(fee))
    assert row["buy_cashflow"] == pytest.approx(float(-buys - fee))
    assert row["sell_cashflow"] == pytest.approx(float(sells - fee))
    assert row["total_cost"] == pytest.approx(float(buys - middle + fee))
    assert row["sell_cashflow"] - float(middle) == pytest.approx(-row["total_cost"])


def test_no_order_does_not_charge_the_fixed_commission():
    row = model().option_trade_costs(4, 4.5, contracts=0, fixed_fee=2.5, fee_per_contract=0.5)
    for name in ("commission", "buy_cashflow", "sell_cashflow", "total_cost"):
        assert row[name] == pytest.approx(0)


def test_sale_and_exercise_compare_total_cash_after_different_fees():
    # Synthetic comparison; Hull does not specify an input example for this choice.
    row = model().option_exit_cashflows(2, 4, sale_fee=3, exercise_fee=5)
    assert row["sale"] == pytest.approx(397)
    assert row["exercise"] == pytest.approx(195)
    assert row["sale_minus_exercise"] == pytest.approx(202)
    expected = (Decimal("4") - Decimal("2")) * 100 - Decimal("3") + Decimal("5")
    assert row["sale_minus_exercise"] == pytest.approx(float(expected))


@pytest.mark.parametrize("call", [
    lambda m: m.option_trade_costs(4.5, 4),
    lambda m: m.option_trade_costs(4, 4.5, contracts=-1),
    lambda m: m.option_trade_costs(4, 4.5, multiplier=0),
])
def test_undefined_quote_or_contract_count_rejected(call):
    with pytest.raises(ValueError):
        call(model())
