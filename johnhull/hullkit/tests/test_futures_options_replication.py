"""Hull 18.9 zero-cost futures replication and American stopping."""
import math

import numpy as np
import pytest
from hullkit import _futures_options as futures
from hullkit._binomial_foundations import small_tree_stopping_values


def test_source_one_step_replication_delta_cash_present_value_and_probability():
    result = futures.futures_one_step_replication(30, 33, 28, 4, 0, .06, 1/12)
    assert [result["delta"], result["up_cash"], result["down_cash"], result["probability"]] == pytest.approx([.8, -1.6, -1.6, .4])
    assert result["price"] == pytest.approx(1.592019967, abs=5e-10)
    assert result["initial_portfolio"] == pytest.approx(-1.592, abs=.0005)
    assert [result["up"], result["down"]] == pytest.approx([1.1, 28/30])


@pytest.mark.parametrize("up_payoff,down_payoff", [(4, 0), (0, 1), (7, -2)])
def test_replication_against_independent_two_by_two_futures_bank_system(up_payoff, down_payoff):
    result = futures.futures_one_step_replication(30, 33, 28, up_payoff, down_payoff, .06, 1/12)
    delta, bank = np.linalg.solve([[33-30, math.exp(.06/12)], [28-30, math.exp(.06/12)]], [up_payoff, down_payoff])
    assert [result["delta"], result["price"]] == pytest.approx([delta, bank], abs=1e-14)
    probability = (30-28)/(33-28)
    expected = math.exp(-.06/12)*(probability*up_payoff+(1-probability)*down_payoff)
    assert result["price"] == pytest.approx(expected, abs=1e-14)


def test_futures_entry_cost_zero_and_option_receipt_replicates_terminal_cash():
    result = futures.futures_one_step_replication(30, 33, 28, 4, 0, .06, 1/12)
    assert result["futures_entry_value"] == pytest.approx(0)
    for price, payoff in [(33, 4), (28, 0)]:
        funded_profit = result["price"]*math.exp(.06/12)+result["delta"]*(price-30)-payoff
        assert funded_profit == pytest.approx(0, abs=1e-14)


def test_referenced_example_13_3_american_futures_put():
    result = futures.futures_exercise_comparison(31, 30, .05, .3, .75, 3, kind="put")
    assert result["american"] == pytest.approx(2.84, abs=.005)
    assert result["probability"] == pytest.approx(.4626, abs=5e-5)
    assert result["growth"] == pytest.approx(1, abs=1e-14)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_futures_american_tree_against_independent_all_stopping_policies(kind):
    result = futures.futures_exercise_comparison(31, 30, .05, .3, .75, 3, kind=kind)
    up = math.exp(.3*math.sqrt(.75/3))
    reference = small_tree_stopping_values(31, 30, .05, .75, 3, up, 1/up, q=.05, kind=kind)
    assert result["american"] == pytest.approx(reference["price"], abs=1e-13)


def test_two_state_prices_must_bracket_initial_futures():
    with pytest.raises(ValueError):
        futures.futures_one_step_replication(30, 33, 31, 4, 0, .06, 1/12)
