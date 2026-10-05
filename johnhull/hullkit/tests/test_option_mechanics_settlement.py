"""Hull §10.3: index cash settlement and independent futures-exercise cashflows."""

import numpy as np
import pytest
from hullkit._option_mechanics import option_cashflows


def test_printed_index_cash_settlement_1200_and_writer_payment():
    buyer = option_cashflows(992, 980, 0, multiplier=100)
    writer = option_cashflows(992, 980, 0, quantity=-1, multiplier=100)
    assert buyer["payoff"] == pytest.approx(1200)
    assert writer["payoff"] == pytest.approx(-1200)
    # Independent settlement accounting: market value less the strike cash leg.
    assert buyer["payoff"] == pytest.approx(992 * 100 - 980 * 100)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_futures_option_exercise_cash_against_separate_contract_cash_legs(kind):
    futures = np.array([-30, -25, -20, 0, 25, 50])
    strike = -25
    sign = 1 if kind == "call" else -1
    settlement = sign * futures * 10 - sign * strike * 10
    exercise_cash = np.where(settlement > 0, settlement, 0)
    actual = option_cashflows(futures, strike, 0, kind=kind, quantity=2, multiplier=10)
    assert np.allclose(actual["payoff"], 2 * exercise_cash, atol=1e-12, rtol=1e-12)
