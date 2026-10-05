"""Hull GE section 13.1: replication, signed borrowing and price arbitrage."""

import math

import numpy as np
import pytest
from hullkit import _binomial_foundations as foundations


def test_hull_one_step_printed_replication_and_cash_values():
    result = foundations.one_step_replication(20, 22, 18, 1, 0, .04, .25)
    assert result["delta"] == pytest.approx(.25)
    assert -result["terminal_bank"] == pytest.approx(4.5)
    assert -result["bank"] == pytest.approx(4.455, abs=.0005)
    assert result["price"] == pytest.approx(.545, abs=.0005)
    assert result["probability"] == pytest.approx(.5503, abs=.00005)
    independent = np.linalg.solve([[22, math.exp(.01)], [18, math.exp(.01)]], [1, 0])
    assert [result["delta"], result["bank"]] == pytest.approx(independent, abs=1e-12)
    assert result["price"] == pytest.approx(independent[0]*20+independent[1], abs=1e-12)


def test_hull_400_options_100_shares_scale_and_mispricing_arbitrage():
    result = foundations.one_step_replication(20, 22, 18, 400, 0, .04, .25)
    assert result["delta"] == pytest.approx(100)
    assert result["price"] == pytest.approx(400*.544775748, abs=1e-6)
    for terminal, payoff in [(22, 400), (18, 0)]:
        assert result["delta"]*terminal+result["bank"]*math.exp(.01) == pytest.approx(payoff, abs=1e-10)
    for quote in [200, 240]:
        trade_sign = 1 if quote < result["price"] else -1
        initial_credit = trade_sign*(result["price"]-quote)
        assert initial_credit > 0
        for terminal, payoff in [(22, 400), (18, 0)]:
            hedge = result["delta"]*terminal+result["bank"]*math.exp(.01)
            assert trade_sign*(payoff-hedge)+initial_credit*math.exp(.01) > 0


def test_singular_states_and_arbitrage_growth_rejected():
    with pytest.raises(ValueError):
        foundations.one_step_replication(20, 20, 20, 1, 0, .04, .25)
    with pytest.raises(ValueError):
        foundations.one_step_replication(20, 22, 18, 1, 0, .5, 1)
