"""Hull Example5.3 income reinvestment."""

import math

import pytest
from hullkit import _forward_pricing as f


def test_source_two_yield_values():
    q = 2 * math.log(1.02)
    assert 100 * q == pytest.approx(3.96, abs=0.005)
    assert f.known_yield_forward(25, 0.1, q, 0.5) == pytest.approx(25.77, abs=0.005)


def test_independent_terminal_shares_and_loan_cash():
    shares = 1.02
    loan = 25 * math.exp(0.1 * 0.5)
    price = loan / shares
    assert f.known_yield_forward(25, 0.1, 2 * math.log(shares), 0.5) == pytest.approx(price)
    assert f.known_yield_forward(25, 0.1, 0, 0.5) == pytest.approx(
        f.no_income_forward(25, 0.1, 0.5)
    )
