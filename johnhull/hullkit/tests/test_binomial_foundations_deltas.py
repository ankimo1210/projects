"""Hull GE section 13.6: node stock-bank hedges versus independent solves."""

import math

import numpy as np
import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.trees import binomial_tree


def test_hull_call_deltas_at_one_step_root_and_two_step_children():
    one_stock, one_options = binomial_tree(20, 21, 0.04, 0.25, 1, 1.1, 0.9)
    one = foundations.replication_grid(one_stock, one_options, 0.04, 0.25)
    assert one["deltas"][0][0] == pytest.approx(0.25, abs=1e-12)
    stock, options = binomial_tree(20, 21, 0.04, 0.5, 2, 1.1, 0.9)
    grid = foundations.replication_grid(stock, options, 0.04, 0.25)
    assert grid["deltas"][0][0] == pytest.approx(0.4358, abs=0.00005)
    assert grid["deltas"][1] == pytest.approx([0.7273, 0], abs=0.00005)
    for t in range(2):
        for j in range(t + 1):
            matrix = [[stock[t + 1][j], math.exp(0.01)], [stock[t + 1][j + 1], math.exp(0.01)]]
            delta, bank = np.linalg.solve(matrix, options[t + 1][j : j + 2])
            assert grid["deltas"][t][j] == pytest.approx(delta, abs=1e-12)
            assert grid["bank"][t][j] == pytest.approx(bank, abs=1e-12)
            assert delta * stock[t][j] + bank == pytest.approx(options[t][j], abs=1e-12)


def test_hull_put_delta_distinguishes_printed_child_rounding():
    stock, raw = binomial_tree(50, 52, 0.05, 2, 2, 1.2, 0.8, kind="put")
    printed = [np.array([4.1923]), np.array([1.4147, 9.4636]), np.array([0, 4, 20])]
    source = foundations.replication_grid(stock, printed, 0.05, 1)
    assert source["deltas"][0][0] == pytest.approx(-0.4024, abs=0.00005)
    assert source["deltas"][1] == pytest.approx([-0.1667, -1], abs=0.00005)
    raw_grid = foundations.replication_grid(stock, raw, 0.05, 1)
    assert raw_grid["deltas"][0][0] == pytest.approx(-0.40245885, abs=1e-8)
    delta, bank = np.linalg.solve([[60, math.exp(0.05)], [40, math.exp(0.05)]], printed[1])
    assert source["deltas"][0][0] == pytest.approx(delta, abs=1e-12)
    assert source["bank"][0][0] == pytest.approx(bank, abs=1e-12)


def test_finite_tree_replication_delta_is_not_the_spot_bump_derivative():
    stock, options = binomial_tree(20, 21, 0.04, 0.25, 1, 1.1, 0.9)
    grid = foundations.replication_grid(stock, options, 0.04, 0.25)
    bump = 0.0001
    high = foundations.terminal_binomial_value(20 + bump, 21, 0.04, 0.25, 1, 1.1, 0.9)["price"]
    low = foundations.terminal_binomial_value(20 - bump, 21, 0.04, 0.25, 1, 1.1, 0.9)["price"]
    derivative = (high - low) / (2 * bump)
    p = (math.exp(0.01) - 0.9) / 0.2
    assert derivative == pytest.approx(p * 1.1 * math.exp(-0.01), abs=1e-9)
    assert abs(derivative - grid["deltas"][0][0]) > 0.3
