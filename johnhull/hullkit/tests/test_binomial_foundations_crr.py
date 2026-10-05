"""Hull GE section 13.8: Figure 13.10's full CRR American put tree."""

import math

import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.trees import binomial_tree


def test_hull_crr_coefficients_and_all_figure_13_10_nodes():
    moments = foundations.crr_moments(.3, 1, .05)
    up, down, p = moments["up"], moments["down"], moments["probability"]
    assert [up, down, moments["mean"], p] == pytest.approx([1.3499, .7408, 1.0513, .5097], abs=.00005)
    stock, option = binomial_tree(50, 52, .05, 2, 2, up, down, kind="put", american=True)
    assert stock[1] == pytest.approx([67.49, 37.04], abs=.005)
    assert stock[2] == pytest.approx([91.11, 50, 27.44], abs=.005)
    assert option[0] == pytest.approx([7.43], abs=.005)
    assert option[1] == pytest.approx([.93, 14.96], abs=.005)
    assert option[2] == pytest.approx([0, 2, 24.56], abs=.005)
    # Independent one-step cash expectation versus the exercise decision.
    assert option[1][0] == pytest.approx(math.exp(-.05)*(1-p)*2, abs=1e-12)
    lower_wait = math.exp(-.05)*(p*2+(1-p)*(52-50*down*down))
    assert option[1][1] == pytest.approx(52-50*down, abs=1e-12)
    assert option[1][1] > lower_wait


def test_crr_source_root_matches_all_policies_and_is_not_fixed_twenty_percent_tree():
    up, down = math.exp(.3), math.exp(-.3)
    policies = foundations.small_tree_stopping_values(50, 52, .05, 2, 2, up, down, kind="put")
    assert policies["price"] == pytest.approx(7.428401903, abs=1e-9)
    assert policies["best_mask"] == 4
    _, option = binomial_tree(50, 52, .05, 2, 2, up, down, kind="put", american=True)
    assert policies["price"] == pytest.approx(option[0][0], abs=1e-12)
    fixed = foundations.small_tree_stopping_values(50, 52, .05, 2, 2, 1.2, .8, kind="put")
    assert abs(policies["price"]-fixed["price"]) > 2
