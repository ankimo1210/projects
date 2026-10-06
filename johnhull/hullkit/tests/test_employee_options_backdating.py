"""Hull GE 16.5: only the source intrinsic-value arithmetic, no legal inference."""

from fractions import Fraction

import pytest
from hullkit import _employee_options as employee


def test_source_decision_stock_50_with_backdated_strike_42_has_intrinsic_8():
    actual = employee.equity_award_payoffs(50, 50, 42, 1, 1)
    reported = employee.equity_award_payoffs(42, 42, 42, 1, 1)
    assert actual["indexed_option_payoff"] == pytest.approx(8)
    assert reported["indexed_option_payoff"] == pytest.approx(0)
    assert actual["indexed_option_payoff"]-reported["indexed_option_payoff"] == pytest.approx(8)


def test_intrinsic_against_independent_fraction_exercise_cash_ledger():
    strike_cash, stock_sale = Fraction(-42), Fraction(50)
    employee_gain = stock_sale+strike_cash
    writer_loss = -stock_sale-strike_cash
    result = employee.mirrored_exercise_cash(50, 42, 1, 1)
    assert result["cash_total"] == pytest.approx(float(employee_gain))
    assert result["cash_total"]+float(writer_loss) == pytest.approx(0)
