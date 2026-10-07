"""Hull Table7.1 quarterly swap cash, not model prices."""

import numpy as np
import pytest
from hullkit import _swap_foundations as s

R = np.array([0.022, 0.026, 0.028, 0.031, 0.033, 0.034, 0.036, 0.038])


def test_source_all_twenty_four_cash_values():
    a = s.interest_swap_cash(1e8, 0.03, R, 0.25)
    assert a["floating"] / 1000 == pytest.approx([550, 650, 700, 775, 825, 850, 900, 950])
    assert a["fixed"] / 1000 == pytest.approx([-750] * 8)
    assert a["net"] / 1000 == pytest.approx([-200, -100, -50, 25, 75, 100, 150, 200])


def test_independent_party_payment_columns():
    a = s.interest_swap_cash(1e8, 0.03, R, 0.25)
    expected = np.array([1e8 * (float(rate) / 4 - 0.03 / 4) for rate in R])
    assert a["net"] == pytest.approx(expected)
    other = s.interest_swap_cash(1e8, 0.03, R, 0.25, receive="fixed")
    assert a["net"] + other["net"] == pytest.approx(np.zeros(8), abs=1e-8)
