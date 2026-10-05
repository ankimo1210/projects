"""Hull GE section 13.3: direct terminal sums versus four paths and recursion."""

import itertools
import math

import numpy as np
import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.trees import binomial_tree


def test_hull_two_step_call_all_stock_payoff_and_option_nodes():
    result = foundations.terminal_binomial_value(20, 21, .04, .5, 2, 1.1, .9)
    assert result["stock"][::-1] == pytest.approx([24.2, 19.8, 16.2], abs=1e-12)
    assert result["payoffs"][::-1] == pytest.approx([3.2, 0, 0], abs=1e-12)
    assert result["price"] == pytest.approx(.9497, abs=.00005)
    children = [foundations.terminal_binomial_value(s, 21, .04, .25, 1, 1.1, .9)["price"] for s in [22, 18]]
    assert children == pytest.approx([1.7433, 0], abs=.00005)
    _, backward = binomial_tree(20, 21, .04, .5, 2, 1.1, .9)
    assert result["price"] == pytest.approx(backward[0][0], abs=1e-12)
    assert children == pytest.approx(backward[1], abs=1e-12)


def test_recombination_preserves_both_paths_to_the_middle_state():
    p = (math.exp(.04*.25)-.9)/.2
    paths = list(itertools.product([1.1, .9], repeat=2))
    probabilities = [math.prod(p if m == 1.1 else 1-p for m in path) for path in paths]
    independent = math.exp(-.04*.5)*sum(w*max(20*math.prod(path)-21, 0) for w, path in zip(probabilities, paths, strict=True))
    result = foundations.terminal_binomial_value(20, 21, .04, .5, 2, 1.1, .9)
    assert result["weights"] == pytest.approx([(1-p)**2, 2*p*(1-p), p*p], abs=1e-12)
    assert result["price"] == pytest.approx(independent, abs=1e-12)
    assert np.sum(result["weights"]*result["stock"]) == pytest.approx(20*math.exp(.02), abs=1e-12)


def test_invalid_tree_and_kind_are_mathematically_rejected():
    with pytest.raises(ValueError):
        foundations.terminal_binomial_value(20, 21, .04, .5, 0, 1.1, .9)
    with pytest.raises(ValueError):
        foundations.terminal_binomial_value(20, 21, .04, .5, 2, .9, .9)
    with pytest.raises(ValueError):
        foundations.terminal_binomial_value(20, 21, .04, .5, 2, 1.1, .9, kind="unknown")
