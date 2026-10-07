"""Hull §4.11 formulas; all extra numbers are explicitly derived/synthetic."""

import numpy as np
import pytest
from hullkit import _rates_foundations as r


def test_source_convexity_formula_and_same_duration_cash_distribution():
    t = np.arange(0.5, 3.01, 0.5)
    cf = np.array([5, 5, 5, 5, 5, 105])
    a = r.bond_sensitivities(t, cf, 0.12)
    assert a["convexity"] == pytest.approx(7.570, abs=0.0005)
    change = r.bond_taylor_change(t, cf, 0.12, 0.02)
    actual = r.bond_sensitivities(t, cf, 0.14)["price"] - a["price"]
    assert abs(change["second_order"] - actual) < abs(change["first_order"] - actual)
    barbell = r.bond_sensitivities([1, 5], [0.5 * np.exp(0.04), 0.5 * np.exp(0.2)], 0.04)
    bullet = r.bond_sensitivities([3], [np.exp(0.12)], 0.04)
    assert barbell["macaulay"] == pytest.approx(bullet["macaulay"])
    assert barbell["convexity"] > bullet["convexity"]


def test_independent_second_price_difference_and_moment_immunization():
    t = np.array([1.0, 3.0, 7.0])
    weights = r.immunization_weights(t, 4)
    cash = weights * np.exp(0.04 * t)

    def surplus(z):
        return np.sum(cash * np.exp(-z * t)) - np.exp(0.16) * np.exp(-z * 4)

    e = 1e-4
    assert surplus(0.04) == pytest.approx(0, abs=1e-12)
    assert (surplus(0.04 + e) - surplus(0.04 - e)) / (2 * e) == pytest.approx(0, abs=1e-6)
    assert (surplus(0.04 + e) - 2 * surplus(0.04) + surplus(0.04 - e)) / e**2 == pytest.approx(
        0, abs=1e-5
    )
    bond = r.bond_sensitivities([0.5, 1, 2], [3, 3, 103], 0.04)

    def price(z):
        return np.dot([3, 3, 103], np.exp(-z * np.array([0.5, 1, 2])))

    gamma = (price(0.04 + e) - 2 * price(0.04) + price(0.04 - e)) / e**2
    assert bond["price_gamma"] == pytest.approx(gamma, rel=1e-7)
    nonparallel = np.sum(cash * np.exp(-(0.04 + np.array([0.001, 0, -0.001])) * t)) - 1
    assert abs(nonparallel) > 1e-4
