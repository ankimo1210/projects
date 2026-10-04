"""§32.4 original node-discount tree and independent nine-path enumeration."""

import importlib
import itertools
import math

import numpy as np
import pytest


def model():
    return importlib.import_module("hullkit._rate_tree")


def test_figure_32_4_reproduces_printed_values_and_independent_path_sum():
    m = model()
    rates = [np.array([0.10]), np.array([0.08, 0.10, 0.12])]
    successors = [np.array([[0, 1, 2]]), np.array([[0, 1, 2], [1, 2, 3], [2, 3, 4]])]
    probability = [np.array([[0.25, 0.5, 0.25]]), np.tile([0.25, 0.5, 0.25], (3, 1))]
    last = np.array([0.06, 0.08, 0.10, 0.12, 0.14])
    payoff = 100 * np.maximum(last - 0.11, 0)
    rows = m.discounted_rollback(rates, successors, probability, [1, 1], payoff)
    assert rows[0][0] == pytest.approx(0.35, abs=0.005)
    assert rows[1] == pytest.approx([0, 0.23, 1.11], abs=0.005)
    expectation = 0
    for first, second in itertools.product(range(3), repeat=2):
        terminal = first + second
        expectation += (
            probability[0][0, first]
            * probability[1][first, second]
            * math.exp(-0.10 - rates[1][first])
            * payoff[terminal]
        )
    assert rows[0][0] == pytest.approx(expectation, abs=1e-13)
    assert rows[0][0] == pytest.approx(0.353128468, abs=1e-9)


@pytest.mark.parametrize("j", [-2, -1, 0, 1, 2])
def test_three_branch_patterns_have_correct_moments_and_nonnegative_probabilities(j):
    row = model().trinomial_branch(j, 0.2, 0.5, 2)
    offsets = row["successors"] - j
    p = row["probabilities"]
    mean = float(p @ offsets)
    assert np.all(p >= 0) and p.sum() == pytest.approx(1, abs=1e-14)
    assert mean == pytest.approx(-0.2 * j * 0.5, abs=1e-14)
    assert p @ (offsets * offsets) - mean * mean == pytest.approx(1 / 3, abs=1e-14)
    if j == 0:
        assert p == pytest.approx([0.1667, 0.6666, 0.1667], abs=0.0001)
    if j == 1:
        assert p[::-1] == pytest.approx([0.1217, 0.6566, 0.2217], abs=0.0001)
    if j == 2:
        assert p[::-1] == pytest.approx([0.8867, 0.0266, 0.0867], abs=0.0001)


def test_exercise_obstacle_uses_the_same_node_discounted_continuation():
    m = model()
    rates = [np.array([0.10]), np.array([0.08, 0.10, 0.12])]
    successors = [np.array([[0, 1, 2]]), np.array([[0, 1, 2], [1, 2, 3], [2, 3, 4]])]
    probs = [np.array([[0.25, 0.5, 0.25]]), np.tile([0.25, 0.5, 0.25], (3, 1))]
    euro = m.discounted_rollback(rates, successors, probs, [1, 1], [0, 0, 0, 1, 3])
    american = m.discounted_rollback(
        rates,
        successors,
        probs,
        [1, 1],
        [0, 0, 0, 1, 3],
        exercise_values=[np.array([0.5]), np.array([0, 0.4, 2])],
    )
    assert american[0][0] >= euro[0][0]
    assert american[1] == pytest.approx([0, 0.4, 2], abs=1e-13)
    assert american[0][0] == pytest.approx(math.exp(-0.1) * (0.5 * 0.4 + 0.25 * 2), abs=1e-13)


def test_undefined_moment_match_and_bad_discount_tree_rejected():
    m = model()
    with pytest.raises(ValueError):
        m.match_trinomial_moments([-1, 0, 1], 2, 0.1)
    with pytest.raises(ValueError):
        m.discounted_rollback([[0.1]], [[[0, 1, 2]]], [[[0.25, 0.5, 0.25]]], [-1], [0, 1, 2])
