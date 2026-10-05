"""Hull GE section 13.5: independently enumerate exercise policies."""

import math

import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.trees import binomial_tree


def test_hull_source_policy_exercises_only_lower_child_and_waits_at_root():
    policies = foundations.small_tree_stopping_values(50, 52, .05, 2, 2, 1.2, .8, kind="put", probability=.6282)
    assert len(policies["policy_values"]) == 8
    assert policies["best_mask"] == 4  # root/up/down exercise bits are 0/1/2.
    assert policies["price"] == pytest.approx(5.0894, abs=.00005)
    assert policies["policy_values"][0] == pytest.approx(4.1923, abs=.00005)
    assert policies["policy_values"][1] == pytest.approx(2, abs=1e-12)
    up_continuation = math.exp(-.05)*(1-.6282)*4
    down_continuation = math.exp(-.05)*(.6282*4+(1-.6282)*20)
    assert up_continuation == pytest.approx(1.4147, abs=.00005)
    assert down_continuation == pytest.approx(9.4636, abs=.00005)
    assert down_continuation < 52-40
    independent = math.exp(-.05)*(.6282*up_continuation+(1-.6282)*12)
    assert policies["price"] == pytest.approx(independent, abs=1e-12)


def test_unrounded_policy_sum_matches_snell_backward_recursion():
    policies = foundations.small_tree_stopping_values(50, 52, .05, 2, 2, 1.2, .8, kind="put")
    _, backward = binomial_tree(50, 52, .05, 2, 2, 1.2, .8, kind="put", american=True)
    european = foundations.terminal_binomial_value(50, 52, .05, 2, 2, 1.2, .8, kind="put")
    assert policies["price"] == pytest.approx(backward[0][0], abs=1e-12)
    assert policies["policy_values"][0] == pytest.approx(european["price"], abs=1e-12)
    assert policies["price"] == pytest.approx(5.089632, abs=.000001)


def test_no_dividend_call_waiting_policy_is_optimal_and_method_is_small_tree_only():
    result = foundations.small_tree_stopping_values(20, 21, .04, .5, 2, 1.1, .9)
    european = foundations.terminal_binomial_value(20, 21, .04, .5, 2, 1.1, .9)
    assert result["price"] == pytest.approx(european["price"], abs=1e-12)
    with pytest.raises(ValueError, match="five"):
        foundations.small_tree_stopping_values(20, 21, .04, .5, 6, 1.1, .9)
