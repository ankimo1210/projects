"""Hull GE 15.8: exercise probabilities, truncated moments and boundaries."""

import math

import pytest
from hullkit import _bsm_foundations as foundations
from hullkit import bsm
from hullkit.trees import crr_price
from scipy.integrate import quad
from scipy.stats import lognorm


@pytest.mark.parametrize(
    "s,k,r,sigma,t", [(42, 40, 0.1, 0.2, 0.5), (100, 120, 0.01, 0.6, 2), (100, 60, -0.02, 0.15, 1)]
)
def test_source_bsm_decomposition_against_independent_payoff_integrals(s, k, r, sigma, t):
    result = foundations.bsm_call_decomposition(s, k, r, sigma, t)
    density = lognorm(s=sigma * math.sqrt(t), scale=s * math.exp((r - sigma**2 / 2) * t))
    probability = quad(density.pdf, k, math.inf, epsabs=1e-10)[0]
    moment = quad(lambda stock: stock * density.pdf(stock), k, math.inf, epsabs=1e-9)[0]
    call = (
        math.exp(-r * t)
        * quad(lambda stock: (stock - k) * density.pdf(stock), k, math.inf, epsabs=1e-9)[0]
    )
    assert result["exercise_probability"] == pytest.approx(probability, abs=1e-10)
    assert result["truncated_mean"] == pytest.approx(moment, abs=1e-8)
    assert result["conditional_mean"] == pytest.approx(moment / probability, abs=1e-8)
    assert result["stock_weight"] == pytest.approx(moment / (s * math.exp(r * t)), abs=1e-10)
    assert result["stock_weight"] > result["exercise_probability"]
    assert result["price"] == pytest.approx(call, abs=1e-8)
    assert result["price"] == pytest.approx(float(bsm.call_price(s, k, r, sigma, t)), abs=1e-12)
    assert result["price"] - float(bsm.put_price(s, k, r, sigma, t)) == pytest.approx(
        s - k * math.exp(-r * t), abs=1e-12
    )


@pytest.mark.parametrize("s", [30, 50])
def test_zero_volatility_discounted_deterministic_payoff(s):
    result = foundations.bsm_call_decomposition(s, 40, 0.1, 0, 0.5)
    terminal = s * math.exp(0.05)
    assert result["price"] == pytest.approx(math.exp(-0.05) * max(terminal - 40, 0))
    assert result["exercise_probability"] == pytest.approx(float(terminal > 40))
    assert result["d1"] is None and result["d2"] is None
    if terminal <= 40:
        assert result["conditional_mean"] is None


@pytest.mark.parametrize("s", [30, 40, 50])
def test_expiry_uses_strict_exercise_event_and_intrinsic(s):
    result = foundations.bsm_call_decomposition(s, 40, 0.1, 0.2, 0)
    assert result["price"] == pytest.approx(max(s - 40, 0))
    assert result["exercise_probability"] == pytest.approx(float(s > 40))


def test_zero_strike_call_is_stock_and_full_truncated_moment():
    result = foundations.bsm_call_decomposition(42, 0, 0.1, 0.2, 0.5)
    assert result["price"] == pytest.approx(42)
    assert result["exercise_probability"] == pytest.approx(1)
    assert result["truncated_mean"] == pytest.approx(42 * math.exp(0.05))


def test_call_against_independent_crr_tree_limit():
    result = foundations.bsm_call_decomposition(42, 40, 0.1, 0.2, 0.5)
    assert result["price"] == pytest.approx(crr_price(42, 40, 0.1, 0.2, 0.5, 1600), abs=0.005)
