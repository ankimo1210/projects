"""Hull GE §1.3 nine printed amounts and independent two-state forward replication."""

from decimal import Decimal

import numpy as np
import pytest
from hullkit import _intro_contracts as c


def test_source_fx_forward_all_delivery_and_payoff_amounts():
    long = c.forward_cashflows(1_000_000, 1.2230, [1.3, 1.2])
    assert long["delivery_cash"] == pytest.approx(-1_223_000)
    assert long["payoff"] == pytest.approx([77_000, -23_000])
    unit = c.forward_cashflows(1, 1.2230, [1.3, 1.2])
    assert unit["payoff"] == pytest.approx([0.077, -0.023])
    short = c.forward_cashflows(1_000_000, 1.2230, [1.3, 1.2], side="short")
    assert short["payoff"] == pytest.approx(-long["payoff"])


def test_source_annual_five_percent_carry_and_reversal_against_decimal_cash_account():
    high = c.simple_carry_comparison(60, 67, 0.05, 1)
    low = c.simple_carry_comparison(60, 58, 0.05, 1)
    assert [
        high["financed_spot"],
        high["interest"],
        high["relative_gain"],
        low["relative_gain"],
    ] == pytest.approx([63, 3, 4, 5])
    loan = Decimal("60") * (1 + Decimal(".05"))
    assert high["relative_gain"] == pytest.approx(float(Decimal("67") - loan))
    assert low["relative_gain"] == pytest.approx(float(loan - Decimal("58")))
    assert high["direction"] == "cash_and_carry"
    assert low["direction"] == "reverse_carry"


def test_fair_forward_against_independent_risk_neutral_tree_and_state_replication():
    fair = c.simple_carry_comparison(60, 63, 0.05, 1)["financed_spot"]
    states = np.array([78.0, 48.0])
    payoff = c.forward_cashflows(1, fair, states)["payoff"]
    probability = (1.05 - 0.8) / (1.3 - 0.8)
    value = (probability * payoff[0] + (1 - probability) * payoff[1]) / 1.05
    holdings = np.linalg.solve(np.column_stack([states, np.full(2, 1.05)]), payoff)
    assert value == pytest.approx(0, abs=1e-13)
    assert holdings == pytest.approx([1, -60])
    assert holdings @ np.array([60, 1]) == pytest.approx(value, abs=1e-13)
    with pytest.raises(ValueError):
        c.simple_carry_comparison(60, 63, 0.05, -1)
