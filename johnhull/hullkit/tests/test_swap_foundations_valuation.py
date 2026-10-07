"""Hull Example7.1 seasoned OIS first coupon and all printed table columns."""

import math

import numpy as np
import pytest
from hullkit import _swap_foundations as s

T = np.array([0.2, 0.7, 1.2])
Z = np.array([0.028, 0.032, 0.034])


def test_source_all_twenty_two_values():
    a = s.ois_swap_value(1e8, 0.03, T, Z, observed_rate=0.023, elapsed=0.3)
    assert 100 * a["continuous_rates"] == pytest.approx([2.50, 3.36, 3.68], abs=0.005)
    assert 100 * a["simple_rates"] == pytest.approx([2.516, 3.388, 3.714], abs=0.0005)
    assert a["fixed_cash"] / 1e6 == pytest.approx([-1.5] * 3)
    assert a["floating_cash"] / 1e6 == pytest.approx([1.258, 1.694, 1.857], abs=0.0005)
    assert a["net_cash"] / 1e6 == pytest.approx([-0.242, 0.194, 0.357], abs=0.0005)
    assert a["discounts"] == pytest.approx([0.9944, 0.9778, 0.9600], abs=0.00005)
    assert a["present_values"] / 1e6 == pytest.approx([-0.241, 0.190, 0.343], abs=0.0005)
    assert a["value"] / 1e6 == pytest.approx(0.292, abs=0.0005)


def test_independent_floating_bond_and_fixed_bond_replication():
    a = s.ois_swap_value(1e8, 0.03, T, Z, observed_rate=0.023, elapsed=0.3)
    floating_bond = 1e8 * math.exp(0.023 * 0.3)
    fixed_bond = np.dot(np.full(3, 1.5e6), np.exp(-T * Z)) + 1e8 * math.exp(-1.2 * 0.034)
    assert a["value"] == pytest.approx(floating_bond - fixed_bond, abs=1e-7)
    assert a["value"] / 1e6 == pytest.approx(0.291845813, abs=1e-9)
    assert s.ois_swap_value(1e8, 0.03, T, Z, observed_rate=0.023, elapsed=0.3, receive="fixed")[
        "value"
    ] == pytest.approx(-a["value"])
