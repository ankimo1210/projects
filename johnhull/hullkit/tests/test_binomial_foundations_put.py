"""Hull GE section 13.4: source rounding and the raw European put."""

import math

import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.trees import binomial_tree


def test_hull_rounded_probability_reproduces_all_put_nodes():
    source = foundations.terminal_binomial_value(50, 52, .05, 2, 2, 1.2, .8, kind="put", probability=.6282)
    assert source["stock"][::-1] == pytest.approx([72, 48, 32], abs=1e-12)
    assert source["payoffs"][::-1] == pytest.approx([0, 4, 20], abs=1e-12)
    children = [foundations.terminal_binomial_value(s, 52, .05, 1, 1, 1.2, .8, kind="put", probability=.6282)["price"] for s in [60, 40]]
    assert children == pytest.approx([1.4147, 9.4636], abs=.00005)
    assert source["price"] == pytest.approx(4.1923, abs=.00005)
    assert source["probability"] == pytest.approx(.6282, abs=1e-12)


def test_unrounded_put_matches_independent_three_state_polynomial_and_backward_tree():
    raw = foundations.terminal_binomial_value(50, 52, .05, 2, 2, 1.2, .8, kind="put")
    p = (math.exp(.05)-.8)/.4
    direct = math.exp(-.1)*(8*p*(1-p)+20*(1-p)**2)
    _, backward = binomial_tree(50, 52, .05, 2, 2, 1.2, .8, kind="put")
    assert raw["price"] == pytest.approx(direct, abs=1e-12)
    assert raw["price"] == pytest.approx(backward[0][0], abs=1e-12)
    assert raw["price"] == pytest.approx(4.192654, abs=.000001)
    assert raw["price"]-4.1923 > .0003


def test_raw_put_call_parity_and_discounted_stock_growth():
    call = foundations.terminal_binomial_value(50, 52, .05, 2, 2, 1.2, .8)
    put = foundations.terminal_binomial_value(50, 52, .05, 2, 2, 1.2, .8, kind="put")
    assert call["price"]-put["price"] == pytest.approx(50-52*math.exp(-.1), abs=1e-12)
    assert math.exp(-.1)*(call["weights"] @ call["stock"]) == pytest.approx(50, abs=1e-12)
