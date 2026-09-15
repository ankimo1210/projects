"""Independent extrema-tail checks for Hull 11e GE section 26.11, pp.623-625.

The oracle integrates the finite-time maximum law of drifted Brownian motion,
obtained from the reflection principle. It uses neither a lookback closed form
nor a floating/fixed parity to price a contract. Minimum tails follow by applying
the maximum law to minus the log price. All markets are synthetic; prices,
strikes and historical extremes are in currency, T in years, and r/q/sigma are
annualized. Continuous monitoring includes today and expiry; positive S/T/sigma
and valid historical extremes are assumed. The production r=q limit is excluded.

Reflection-principle reference: MIT 6.265/15.070J, Fall 2013, Lecture 7,
Proposition 2 (joint terminal/maximum law), extended here by exponential tilting:
https://ocw.mit.edu/courses/15-070j-advanced-stochastic-processes-fall-2013/
aca1518a09539a09ddd37428ab0d0268_MIT15_070JF13_Lec7.pdf
"""

import math
from typing import NamedTuple

import pytest
from hullkit import exotics
from scipy.integrate import quad
from scipy.special import log_ndtr


class Market(NamedTuple):
    spot: float
    rate: float
    volatility: float
    expiry: float
    dividend: float


MARKETS = [
    pytest.param(Market(50, 0.10, 0.40, 0.25, 0.0), id="hull-example-26-2"),
    pytest.param(Market(100, 0.05, 0.20, 1.0, 0.02), id="positive-carry"),
    pytest.param(Market(100, 0.01, 0.25, 1.5, 0.07), id="dividend-above-rate"),
    pytest.param(Market(100, -0.025, 0.18, 0.75, 0.01), id="negative-rate"),
    pytest.param(Market(100, 0.03, 0.15, 1 / 365, 0.01), id="near-expiry"),
    pytest.param(Market(100, 0.06, 0.70, 5.0, 0.025), id="long-high-vol"),
    pytest.param(Market(100, 0.0301, 0.30, 2.0, 0.03), id="small-positive-carry"),
    pytest.param(Market(100, 0.03, 0.30, 2.0, 0.0301), id="small-negative-carry"),
]
HISTORIES = [
    pytest.param((1.0, 1.0), id="new"),
    pytest.param((0.85, 1.20), id="seasoned"),
]
CONTRACTS = (
    "floating_call",
    "floating_put",
    "fixed_call",
    "fixed_put",
)
STRIKE_RATIOS = (0.75, 1.0, 1.35)
ABS_TOL = 2e-9
REL_TOL = 2e-11


def _discounted_tail(market, threshold, *, maximum):
    """Integrate the upper-price tail or lower-price CDF, in currency units.

    For X_t=mu*t+sigma*W_t and y>=0, P(max X>=y) equals
    Phi((mu*T-y)/s) + exp(2*mu*y/sigma**2)*Phi((-mu*T-y)/s), s=sigma*sqrt(T).
    Integrating S*exp(y) times this law gives the maximum-price tail.
    Changing mu to -mu and exp(y) to exp(-y) gives the minimum-price tail.
    """
    spot, rate, sigma, expiry, dividend = market
    sign = 1 if maximum else -1
    drift = sign * (rate - dividend - 0.5 * sigma**2)
    scale = sigma * math.sqrt(expiry)
    lower = sign * math.log(threshold / spot)
    assert lower >= 0

    def integrand(u):
        y = lower + scale * u
        # Combine exponents: neither the price nor the tilt can overflow first.
        direct = sign * y + log_ndtr((drift * expiry - y) / scale)
        reflected = sign * y + 2 * drift * y / sigma**2 + log_ndtr((-drift * expiry - y) / scale)
        return math.exp(direct) + math.exp(reflected)

    value, estimated_error = quad(integrand, 0, math.inf, epsabs=1e-13, epsrel=1e-13)
    factor = spot * scale * math.exp(-rate * expiry)
    # QUADPACK's estimate is not a rigorous error bound.
    assert factor * estimated_error < ABS_TOL / 10
    return factor * value


def _reference_price(market, contract, history, strike_ratio=1.0):
    """Price each payoff directly from its own extreme-tail expectation."""
    spot, rate, _, expiry, dividend = market
    minimum, maximum = (spot * x for x in history)
    strike = spot * strike_ratio
    discount = math.exp(-rate * expiry)
    discounted_terminal = spot * math.exp(-dividend * expiry)
    if contract == "floating_call":
        return (
            discounted_terminal
            - discount * minimum
            + _discounted_tail(market, minimum, maximum=False)
        )
    if contract == "floating_put":
        return (
            discount * maximum
            + _discounted_tail(market, maximum, maximum=True)
            - discounted_terminal
        )
    if contract == "fixed_call":
        return discount * max(maximum - strike, 0) + _discounted_tail(
            market, max(maximum, strike), maximum=True
        )
    if contract == "fixed_put":
        return discount * max(strike - minimum, 0) + _discounted_tail(
            market, min(minimum, strike), maximum=False
        )
    raise ValueError(contract)


def _production_price(market, contract, history, strike_ratio=1.0):
    spot, rate, sigma, expiry, dividend = market
    minimum, maximum = (spot * x for x in history)
    extreme = minimum if contract in ("floating_call", "fixed_put") else maximum
    args = [spot, extreme, rate, sigma, expiry, dividend]
    if contract.startswith("fixed"):
        args.insert(1, spot * strike_ratio)
    return getattr(exotics, "lookback_" + contract)(*args)


def _assert_reference(market, contract, history, strike_ratio=1.0):
    actual = _production_price(market, contract, history, strike_ratio)
    expected = _reference_price(market, contract, history, strike_ratio)
    assert actual == pytest.approx(expected, abs=ABS_TOL, rel=REL_TOL)


@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("history", HISTORIES)
@pytest.mark.parametrize("contract", CONTRACTS[:2])
def test_floating_lookback_against_extrema_tail(market, history, contract):
    _assert_reference(market, contract, history)


@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("history", HISTORIES)
@pytest.mark.parametrize("contract", CONTRACTS[2:])
@pytest.mark.parametrize("strike_ratio", STRIKE_RATIOS)
def test_fixed_lookback_against_extrema_tail(market, history, contract, strike_ratio):
    _assert_reference(market, contract, history, strike_ratio)


@pytest.mark.parametrize(("contract", "printed"), [("floating_call", 8.04), ("floating_put", 7.79)])
def test_extrema_oracle_reproduces_both_hull_example_prices(contract, printed):
    expected = _reference_price(Market(50, 0.10, 0.40, 0.25, 0.0), contract, (1.0, 1.0))
    assert expected == pytest.approx(printed, abs=0.005)


@pytest.mark.parametrize(
    ("floating", "fixed"), [("floating_call", "fixed_put"), ("floating_put", "fixed_call")]
)
def test_independent_prices_reject_shared_parity_preserving_bias(monkeypatch, floating, fixed):
    """A wrong floating price shifts its fixed counterpart while preserving parity."""
    market = Market(100, 0.05, 0.20, 1.0, 0.02)
    history = (0.85, 1.20)
    original = getattr(exotics, "lookback_" + floating)
    monkeypatch.setattr(exotics, "lookback_" + floating, lambda *a, **kw: original(*a, **kw) + 0.25)
    floating_price = _production_price(market, floating, history)
    fixed_price = _production_price(market, fixed, history)
    forward = market.spot * (
        math.exp(-market.dividend * market.expiry) - math.exp(-market.rate * market.expiry)
    )
    signed_forward = forward if fixed == "fixed_call" else -forward
    assert fixed_price == pytest.approx(floating_price + signed_forward, abs=ABS_TOL, rel=REL_TOL)
    for contract in (floating, fixed):
        with pytest.raises(AssertionError):
            _assert_reference(market, contract, history)
