"""Hull §36.1 DCF and independent replicated physical option returns."""

import math

import numpy as np
import pytest
from hullkit import _real_options_foundations as r
from scipy.optimize import brentq


def test_source_npv_and_call_put_required_returns():
    npv = r.real_project_npv(100, [1, 2, 3, 4, 5], [25] * 5, 0.12)
    assert npv == pytest.approx(-11.53, rel=0, abs=0.005)
    result = r.two_state_required_returns(20, 22, 18, 21, 0.04, 0.10, 0.25)
    assert result["call"]["price"] == pytest.approx(0.545, rel=0, abs=0.0005)
    assert 100 * result["call"]["required_return"] == pytest.approx(55.96, rel=0, abs=0.005)
    assert 100 * result["put"]["required_return"] == pytest.approx(-70.4, rel=0, abs=0.05)


def test_independent_terminal_cash_replication_and_required_rate_root():
    terminal = -100 * math.exp(0.12 * 5) + sum(25 * math.exp(0.12 * (5 - t)) for t in range(1, 6))
    assert r.real_project_npv(100, list(range(1, 6)), [25] * 5, 0.12) == pytest.approx(
        terminal * math.exp(-0.6)
    )
    result = r.two_state_required_returns(20, 22, 18, 21, 0.04, 0.1, 0.25)
    for kind in ["call", "put"]:
        payoffs = (
            np.maximum(np.array([22, 18]) - 21, 0)
            if kind == "call"
            else np.maximum(21 - np.array([22, 18]), 0)
        )
        delta, cash_at_maturity = np.linalg.solve([[22, 1], [18, 1]], payoffs)
        price = delta * 20 + cash_at_maturity * math.exp(-0.04 * 0.25)
        a = result[kind]
        assert a["price"] == pytest.approx(price, abs=1e-13)
        assert a["delta"] == pytest.approx(delta)
        probabilities = [result["p_physical"], 1 - result["p_physical"]]
        physical_payoff = np.dot(probabilities, payoffs)
        root = brentq(
            lambda rate, physical_payoff=physical_payoff, price=price: (
                physical_payoff * math.exp(-rate * 0.25) - price
            ),
            -5,
            5,
        )
        assert a["required_return"] == pytest.approx(root, abs=1e-12)
