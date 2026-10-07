"""Hull §7.3 four borrowing/investment transformations."""

import numpy as np
import pytest
from hullkit import _swap_foundations as s

LEGS = [
    [(1, 0.001), (0, 0.03), (-1, 0)],
    [(0, 0.032), (1, 0), (0, -0.0297)],
    [(0, 0.027), (1, 0), (0, -0.03)],
    [(1, -0.002), (0, 0.0297), (-1, 0)],
]


def test_source_four_effective_rates():
    outputs = [s.effective_rate(legs) for legs in LEGS]
    assert [x["fixed_spread"] for x in outputs] == pytest.approx([0.031, 0.0023, -0.003, 0.0277])
    assert [x["floating_loading"] for x in outputs] == pytest.approx([0, 1, 1, 0])


def test_independent_cash_at_two_floating_states():
    for legs in LEGS:
        a = s.effective_rate(legs)
        for market in [0.01, 0.06]:
            cash = sum(1e8 * 0.25 * (loading * market + spread) for loading, spread in legs)
            assert 1e8 * 0.25 * (
                a["floating_loading"] * market + a["fixed_spread"]
            ) == pytest.approx(cash)
    assert np.array(LEGS).shape == (4, 3, 2)
